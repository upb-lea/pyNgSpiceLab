"""
Circuit Handler Module.

This module performs the initialization and validation of the circuit.
It keeps track of important information about the circuit configurations and can share this data if requested by any other module.
"""

# python libraries
import os
import logging
from typing import List
from pathlib import Path

# 3rd party libraries
from spicelib import SpiceEditor

# own libraries
from dtos import ConfigInfoDto, UserRequestDto

# configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitHandler:
    """Class that handles circuit initialization and configuration information management."""

    _circuit_info: List[ConfigInfoDto]  # contains all the circuit's configurations information

    def __init__(self):
        """Initialize the member varaiables of the CircuitHandler class."""
        self._circuit_info = []

    def initialize_circuit(self, request: UserRequestDto) -> bool:
        """
        Validate the schematic file path and the circuit configuration parameters.
        
        :param request: User request containing the config and library data.
        :type request: UserRequestDto
        :return: True, if schematic file path exists, configurations parameters are consistent and adapted schematic is created succesfully.
        :rtype: bool
        """
        logger.info("Initialization of the circuit configuration started.")

        # Variable declaration
        schematic_file_path = request.circuit_path  # Main circuit topology schematic file path
        config_params_list = request.configurations  # List of configurations provided by the user
        lib_map = request.library_map
        is_consistent: bool = True

        # Check schematic file
        if not self._validate_schematic(schematic_file_path):
            is_consistent = False
            logger. info("Schematic validation failed.")
            return is_consistent

        # Check the configuration parameters
        if not self._validate_configs(schematic_file_path, config_params_list):
            is_consistent = False
            logger.info("Configuration validation failed.")
            return is_consistent

        # Adapt schematic for each configuration
        logger.info("Configuration schematic adaption started.")
        for config in config_params_list:
            self._adapt_schematic_file(config, lib_map)
        logger.info("Configuration schematic adaption complete.")
        
        logger.info("Initialization of the circuit configuration completed.")
        return is_consistent

    def _validate_schematic(self, schematic_file_path: str) -> bool:
        """Verify the existence of main schematic file and other necessary checks if required."""
        if not os.path.exists(schematic_file_path):
            logger.warning(f"Schematic file not found: {schematic_file_path}")
            return False

        logger.info("Schematic file path is valid.")
        return True
        
    def _validate_configs(self, schematic_file_path: str, config_params_list: List[ConfigInfoDto]) -> bool:
        """Validate component names and values in all circuit configurations."""
        # Safety check: Ensure the list isn't empty
        if not config_params_list:
            logger.warning("No configurations provided to validate.")
            return True  # Nothing to fail
        
        # Using the original schematic file path for checking existence of components
        editor = SpiceEditor(schematic_file_path)
        logger.info(f"circuit_path: {schematic_file_path}")

        # Create a list of all the components present in the netlist
        all_components = editor.get_components()
        # Bring all the components names into upper case for standard comparison
        all_components_upper = [str(item).upper() for item in all_components]

        # For each configuration check the component names and the values
        for config in config_params_list:
            for component_ref, new_value in config.config_parameters.items():

                # Checking for invalid component names
                if component_ref.upper() not in all_components_upper:
                    logger.error(f"Component '{component_ref}' in configuration number '{config.config_number}' not found in the netlist.")
                    raise ValueError(f"Component '{component_ref}' not found in the circuit schematic file.")

                # Checking for invalid component values
                try:
                    numeric_val = self._parse_float_value(new_value)
                    if numeric_val <= 0:
                        print(f"numeric_value: {numeric_val}")
                        raise ValueError(f"Value must be strictly greater than 0. Got '{numeric_val}'")
                except ValueError as e:
                    if "greater than 0" in str(e):
                        raise
                    raise ValueError(
                        f"Invalid numeric format for '{component_ref}': '{new_value}'"
                    ) from e

        return True

    def _adapt_schematic_file(self, config: ConfigInfoDto, lib_map: dict[str, dict[str, str]]) -> bool:
        """Generate schematic file for configurations with adapted libraries and update the ConfigInfoDto."""
        # Shared and adapter library template definitions
        adapter_lib_template = """\
        .subckt GAN_DEVICE_{pos} G D S
        X{pos} {adapter_subckt}
        .ends GAN_DEVICE_{pos}
        """

        shared_lib_template = """\
        .include "{adapter_path}"
        """

        # Variable that keeps track of the libraries used in a configuration
        used_libraries = set(config.config_libraries.values())

        # Write the paths of the used libraries once in the shared library
        shared_lib_text = "".join(shared_lib_template.format(adapter_path=lib_map[lib]["path"]) for lib in used_libraries)

        if config.config_path is None:
            raise ValueError("Configuration path cannot be None")
        
        shared_lib_path = Path(config.config_path).parent / "shared_library.lib"
        shared_lib_path.write_text(shared_lib_text)

        # Write subcircuit definitions in separate file for each transistor
        transistors_list = config.config_libraries.keys()

        for transistor in transistors_list:
            transistor_lib = config.config_libraries[transistor]
            tmp_lib_text = adapter_lib_template.format(adapter_subckt=lib_map[transistor_lib]["subckt"], pos=transistor)
            tmp_lib_path = Path(config.config_path).parent / f"active_adapter_{transistor}.lib"
            tmp_lib_path.write_text(tmp_lib_text)

        self._circuit_info.append(config)
        return True

    def get_circuit_info(self, config_number: int) -> ConfigInfoDto | None:
        """
        Return all the information of a circuit configuration.
        
        :param config_number: Configuration number of the requested configuration
        :type config_number: int
        :return: Configuration information of the requested configuration number
        :rtype: ConfigInfoDto or None if the configuration does not exists
        """
        # Find config_number in the list of configurations
        for config in self._circuit_info:
            if config.config_number == config_number:
                return config
        
        return None

    @staticmethod
    def _parse_float_value(val_str: str) -> float:
        """Convert a SPICE string value (e.g., '1.5u', '10k', '4.7meg') to a float."""
        val_str = val_str.strip().lower()

        # SPICE multipliers mapping
        multipliers = {
            't': 1e12, 'g': 1e9, 'meg': 1e6, 'k': 1e3,
            'm': 1e-3, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15
        }

        # Multiplier variable declaration
        mult = 1.0

        # Check for suffixes
        for suffix, m in multipliers.items():
            if val_str.endswith(suffix):
                mult = m
                val_str = val_str[:-len(suffix)]
                break

        return float(val_str)*mult
