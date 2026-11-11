"""
Circuit Handler Module.

This module performs the initialization and validation of the circuit.
It keeps track of important information about the circuit configurations and can share this data if requested by any other module.
"""

# python libraries
import os
import logging
from typing import List

# 3rd party libraries

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
        """Boundary checks for the parameters in the all the configurations of the circuit."""
        logger.info("Configuration parameters passed boundary checks.")
        # TODO: Implement the boundary check conditions
        return True

    def _adapt_schematic_file(self, config: ConfigInfoDto, lib_map: dict[str, dict[str, str]]) -> bool:
        """Generate schematic file for configurations with adapted libraries and update the ConfigInfoDto."""
        # TODO: schematic adaption mechanism and update ConfigInfoDto
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
