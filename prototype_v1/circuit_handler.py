"""
Circuit Handler Module.

This module performs the initialization and validation of the circuit.
It keeps track of important information about the circuit configurations and can share this data if requested by any other module.
"""

# python libraries
import os
import logging
from typing import List

# own libraries
from dtos import ConfigInfoDto

# 3rd party libraries


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitHandler:
    """Class that handles circuit initialization and configuration information management."""

    _circuit_info: List[ConfigInfoDto]  # contains all the circuit's configurations information

    def __init__(self):
        """Initialize the member varaiables of the CircuitHandler class."""
        self._circuit_info = []

    def initialize_circuit(self, schematic_file_path: str, config_params_list: List[ConfigInfoDto]) -> bool:
        """
        Validate the schematic file path and the circuit configuration parameters.
        
        :param schematic_file_path: Main circuit topology schematic file path
        :type schematic_file_path: str
        :param config_params_list: List of configurations provided by the user
        :type schematic_file_path: List[ConfigInfoDto]
        :return: True, if schematic file path exists, configurations parameters are consistent and adapted schematic is created succesfully.
        :rtype: bool
        """
        logger.info("Initialization of the circuit configuration started.")

        # Variable declaration
        is_consistent: bool = True

        # Check schematic file and configurations
        if not self._validate_schematic(schematic_file_path) and self._validate_configs(config_params_list):
            is_consistent = False
            return is_consistent

        # Adapt schematic for each configuration
        logger.info("Configuration schematic adaption started.")
        for config in config_params_list:
            self._adapt_schematic_file(config)
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
        
    def _validate_configs(self, config_params_list: List[ConfigInfoDto]) -> bool:
        """Boundary checks for the parameters in the all the configurations of the circuit."""
        logger.info("Configuration parameters passed boundary checks.")
        # TODO: Implement the boundary check conditions
        return True

    def _adapt_schematic_file(self, config: ConfigInfoDto) -> bool:
        """Generate schematic file for configurations with adapted libraries and update the ConfigInfoDto."""
        # TODO: schematic adaption mechanism and update ConfigInfoDto
        self._circuit_info.append(config)
        return True

    def get_circuit_info(self, config_number: int) -> ConfigInfoDto:
        """
        Return all the information of a circuit configuration.
        
        :param config_number: Configuration number of the requested configuration
        :type config_number: int
        :return: Configuration information of the requested configuration number
        :rtype: ConfigInfoDto
        """
        # Find config_number in the list of configurations
        for config in self._circuit_info:
            if config.config_number == config_number:
                return config

        raise ValueError(f"Configuration {config_number} not found")
