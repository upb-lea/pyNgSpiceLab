"""
Circuit Handler Module.

This module performs the initialization and validation of the circuit.
It keeps track of important information about the circuit configurations and can share this data if requested by any other module.
"""

# python libraries
import os
import logging
import shutil
from textwrap import dedent
from typing import List
from pathlib import Path

# 3rd party libraries
from spicelib import SpiceEditor

# own libraries
from .dtos import ConfigInfoDto, UserRequestDto

# configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitHandler:
    """Class that handles circuit initialization and configuration information management."""

    _circuit_info: List[ConfigInfoDto]  # contains all the circuit's configurations information
    _schematic_file_path: Path  # the original user provided circuit schematic file path

    def __init__(self):
        """Initialize the member variables of the CircuitHandler class."""
        self._circuit_info = []
        self._schematic_file_path = Path("")

    def initialize_circuit(self, request: UserRequestDto) -> bool:
        """
        Validate the schematic file path and the circuit configuration parameters.
        
        :param request: User request containing the config and library data.
        :type request: UserRequestDto
        :return: True, if schematic file path exists, configurations parameters are consistent and adapted schematic is created successfully.
        :rtype: bool
        """
        logger.info("Initialization of the circuit configuration started.")

        # Variable declaration
        self._schematic_file_path = Path(request.circuit_path)  # Main circuit topology schematic file path
        config_params_list = request.configurations  # List of configurations provided by the user
        lib_map = request.library_map  # Mapping of library name -> {"path": ..., "subckt": ...}
        is_consistent: bool = True

        # Create a copy of user provided netlist
        source_path = Path(self._schematic_file_path)
        if source_path.is_file():
            snapshot_path = source_path.parent / "configurations" / f"{source_path.stem}_snapshot{source_path.suffix}"
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, snapshot_path)

        # Check schematic file
        if not self._validate_schematic(snapshot_path):
            is_consistent = False
            logger. info("Schematic validation failed.")
            return is_consistent

        # Check the configuration parameters
        if not self._validate_configs(config_params_list, snapshot_path):
            is_consistent = False
            logger.info("Configuration validation failed.")
            return is_consistent

        # Adapt schematic for each configuration
        logger.info("Configuration schematic adaption started.")
        for config in config_params_list:
            self._adapt_schematic_file(config, lib_map, snapshot_path)
        logger.info("Configuration schematic adaption complete.")
        
        logger.info("Initialization of the circuit configuration completed.")
        return is_consistent

    def _validate_schematic(self, schematic_file_path: Path) -> bool:
        """
        Verify the existence of main schematic file and other necessary checks if required.

        :return: True, if the schematic path exists and points to a file.
        :rtype: bool
        """
        # The path must exist
        if not os.path.exists(schematic_file_path):
            logger.warning(f"Schematic file not found: {schematic_file_path}")
            return False

        # The path must be a file (not a directory)
        if not Path(schematic_file_path).is_file():
            logger.warning(f"Invalid schematic file: {schematic_file_path}")
            return False

        logger.info("Schematic file path is valid.")
        return True

    def _validate_configs(self, config_params_list: List[ConfigInfoDto], schematic_file_path: Path) -> bool:
        """
        Validate component and voltage source names and values in all configurations.

        :param config_params_list: List of configurations provided by the user.
        :type config_params_list: List[ConfigInfoDto]
        :return: True, if all configurations are valid (or if there is nothing to validate).
        :rtype: bool
        :raises ValueError: If a component or source is missing from the netlist, a voltage source
            is not named V..., a value is empty or not numeric, or a passive value is not strictly positive.
        """
        if not config_params_list:
            logger.warning("No configurations provided to validate.")
            return True

        editor = SpiceEditor(schematic_file_path)
        logger.info(f"circuit_path: {schematic_file_path}")

        # Uppercase all netlist component names for case-insensitive comparison
        all_components_upper = [str(item).upper() for item in editor.get_components()]

        for config in config_params_list:
            # (dictionary, label, is_source) for each group to validate
            groups = [
                (config.config_parameters, "Component", False),
                (config.voltage_sources, "Voltage source", True),
            ]

            for items, label, is_source in groups:
                for ref, new_value in items.items():

                    # Name must exist in the netlist
                    if ref.upper() not in all_components_upper:
                        logger.error(
                            f"{label} '{ref}' in configuration number "
                            f"'{config.config_number}' not found in the netlist."
                        )
                        raise ValueError(f"{label} '{ref}' not found in the circuit schematic file.")

                    # Voltage sources must be named V...
                    if is_source: 
                        if not ref.upper().startswith("V"):
                            raise ValueError(f"'{ref}' is not a voltage source (name must start with 'V').")
                        continue

                    # Value must not be empty
                    value_str = str(new_value).strip()
                    if not value_str:
                        raise ValueError(f"Empty value for {label.lower()} '{ref}'.")

                    # Numeric check
                    try:
                        numeric_val = self._parse_float_value(value_str)
                    except ValueError as e:
                        raise ValueError(
                            f"Invalid numeric format for '{ref}': '{new_value}'"
                        ) from e

                    # Passive components must be > 0; sources may be 0 or negative
                    if numeric_val <= 0:
                        raise ValueError(
                            f"Value for '{ref}' must be strictly greater than 0. Got '{numeric_val}'"
                        )

        return True

    def _adapt_schematic_file(self, config: ConfigInfoDto, lib_map: dict[str, dict[str, str]], schematic_file_path: Path) -> bool:
        """
        Copy the user's netlist, apply this configuration's changes to the copy, and update the ConfigInfoDto.

        :param config: Configuration whose changes are applied to the netlist copy.
        :type config: ConfigInfoDto
        :param lib_map: Mapping of library name to its data (e.g. "path" and "subckt").
        :type lib_map: dict[str, dict[str, str]]
        :return: True, once the adapted netlist is saved and the configuration is registered.
        :rtype: bool
        :raises ValueError: If the configuration path is None.
        """
        if config.config_path is None:
            raise ValueError("Configuration path cannot be None")

        # Generate a different path for the configuration circuit files
        config_path = schematic_file_path.parent / (f"config_{config.config_number}.cir")

        # Update the config path in the config
        config.config_path = str(config_path)

        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy the original netlist (user's file stays untouched)
        shutil.copy2(schematic_file_path, config_path)

        # Write the adapter library files for this configuration
        shared_lib_blocks, adapter_lib_blocks = self._write_adapter_libraries(config, lib_map)

        # Open the COPY and apply all changes to it
        editor = SpiceEditor(str(config_path))

        # Remove original transistor library references
        self._remove_original_transistor_libs(editor, lib_map)

        # Insert the paths to the copied netlist (index 0 is the netlist title line)
        insert_index = 1

        editor.netlist.insert(insert_index, "* Shared Libraries:\n")
        insert_index += 1

        # Insert the shared library include directives
        for shared_lib in shared_lib_blocks:
            editor.netlist.insert(insert_index, f'{shared_lib}\n')
            insert_index += 1

        editor.netlist.insert(insert_index, "* Adapter Libraries:\n")
        insert_index += 1

        # Insert the adapter sub-circuit definitions
        for adapter_lib in adapter_lib_blocks:
            # editor.netlist.insert(insert_index, f'.inc "{adapter_path}"\n')
            editor.netlist.insert(insert_index, f'{adapter_lib}\n')
            insert_index += 1

        # Apply the configuration's values and models to the netlist copy
        self._apply_component_values(editor, config)
        self._apply_voltage_sources(editor, config)
        self._apply_transistor_models(editor, config)
        editor.add_instruction(".options savecurrents")

        # Add the transient analysis command
        tran_cmd = f".{config.sim_type} {config.sim_time_step} {config.sim_time}"
        editor.add_instruction(tran_cmd)

        # Save back to the copy
        editor.save_netlist(str(config_path))

        # Register the adapted configuration
        self._circuit_info.append(config)
        return True

    def _write_adapter_libraries(self, config: ConfigInfoDto, lib_map: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
        """
        Build the shared library include blocks and the per-transistor adapter sub-circuit blocks.

        :param config: Configuration containing the transistor-to-library assignments.
        :type config: ConfigInfoDto
        :param lib_map: Mapping of library name to its data (e.g. "path" and "subckt").
        :type lib_map: dict[str, dict[str, str]]
        :return: Tuple of (shared library include blocks, adapter sub-circuit blocks).
            Note: both elements are lists of strings at runtime.
        :rtype: tuple[str, list[str]]
        :raises ValueError: If the configuration path is None.
        """
        # Adapter library template: sub-circuit wrapping one transistor position
        adapter_lib_template = dedent("""\
        .subckt TRANSISTOR_DEVICE_{position} D G S G
        {position} {adapter_subckt}
        .ends TRANSISTOR_DEVICE_{position}
        """)

        # Shared library template: include directive for a library file
        shared_lib_template = dedent("""\
        .inc "{adapter_path}"
        """)

        # Variable that keeps track of the libraries used in a configuration
        used_libraries = set(config.config_libraries.values())

        shared_lib_blocks = []

        # Create the text to write all libraries used once in the shared library
        for lib in used_libraries:
            shared_lib = "".join(shared_lib_template.format(adapter_path=lib_map[lib]["path"]))
            shared_lib_blocks.append(shared_lib)

        # To avoid code check errors
        if config.config_path is None:
            raise ValueError("Configuration path cannot be None")

        # Configuration files directory
        # config_dir = Path(config.config_path).parent

        # Write the text in the shared library path
        # shared_lib_path = config_dir / "shared_library.lib"
        # shared_lib_path.write_text(shared_lib_text)

        # Write individual adapter libraries
        adapter_lib_blocks = []

        for transistor, transistor_lib in config.config_libraries.items():
            # Format and write text to adapter library files
            adapter_lib = adapter_lib_template.format(
                adapter_subckt=lib_map[transistor_lib]["subckt"],
                position=transistor
            )
            adapter_lib_blocks.append(adapter_lib)

        return shared_lib_blocks, adapter_lib_blocks

    def _remove_original_transistor_libs(self, editor: SpiceEditor, lib_map: dict[str, dict[str, str]]) -> None:
        """
        Remove directives referencing original transistor libraries.

        :param editor: Editor holding the netlist copy to clean.
        :type editor: SpiceEditor
        :param lib_map: Mapping of library name to its data; the "path" file names identify the libraries to remove.
        :type lib_map: dict[str, dict[str, str]]
        :return: None
        :rtype: None
        """
        # File names (lowercase) of the libraries that must be removed
        targets = {Path(library["path"]).name.lower() for library in lib_map.values()}

        # for index, line in enumerate(editor.netlist):
        #     print(index, type(line).__name__, str(line))
            
        # Iterate over a copy because lines are removed while looping
        for line in list(editor.netlist):
            stripped = str(line).strip().lower()

            # Only .lib / .include / .inc directives are of interest
            if not stripped.lower().startswith((".lib ", ".include ", ".inc ")):
                continue

            # Extract the referenced file name from the directive
            referenced_file = Path(stripped.split(maxsplit=1)[1].strip('"')).name.lower()

            if referenced_file in targets:
                editor.remove_instruction(str(line))

    def _apply_component_values(self, editor: SpiceEditor, config: ConfigInfoDto) -> None:
        """
        Set the component values of the configuration in the netlist.

        :param editor: Editor holding the netlist copy to modify.
        :type editor: SpiceEditor
        :param config: Configuration containing the component reference-to-value mapping.
        :type config: ConfigInfoDto
        :return: None
        :rtype: None
        """
        for ref, value in (config.config_parameters or {}).items():
            editor.set_component_value(ref, value)

    def _apply_voltage_sources(self, editor: SpiceEditor, config: ConfigInfoDto) -> None:
        """
        Set the voltage source values or waveforms of the configuration in the netlist.

        :param editor: Editor holding the netlist copy to modify.
        :type editor: SpiceEditor
        :param config: Configuration containing the voltage source reference-to-value mapping.
        :type config: ConfigInfoDto
        :return: None
        :rtype: None
        """
        for ref, value in (config.voltage_sources or {}).items():
            value = str(value).strip()
            if "(" in value:
                editor.set_element_model(ref, value)      # waveform like PULSE(...)
            else:
                editor.set_component_value(ref, value)    # plain DC value

    def _apply_transistor_models(self, editor: SpiceEditor, config: ConfigInfoDto) -> None:
        """
        Assign the generated adapter sub-circuit model to each transistor of the configuration.

        :param editor: Editor holding the netlist copy to modify.
        :type editor: SpiceEditor
        :param config: Configuration containing the transistors to update.
        :type config: ConfigInfoDto
        :return: None
        :rtype: None
        """
        for transistor in config.config_libraries:
            editor.set_element_model(transistor, f"TRANSISTOR_DEVICE_{transistor}")

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
        """
        Convert a SPICE string value (e.g., '1.5u', '10k', '4.7meg') to a float.

        :param val_str: SPICE-formatted numeric string, optionally with a multiplier suffix
        :type val_str: str
        :return: The numeric value with the multiplier applied
        :rtype: float
        :raises ValueError: If the numeric part cannot be converted to a float
        """
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
