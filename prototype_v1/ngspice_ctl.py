"""
Session Handler Module.

This module controls the main program flow and handles all the administrative workflows. 
It communicates with other modules such as Circuit Handler, Simulation Handler, etc
"""

# python libraries
import logging
from typing import List

# 3rd party libraries

# own libraries
from dtos import ConfigInfoDto, UserRequestDto
from circuit_handler import CircuitHandler
from simulation_handler import SimulationHandler
from result_handler import ResultHandler

# configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionHandler:
    """Class that handles the administrative processes of the toolbox."""

    _circuit_handler: CircuitHandler
    _simulation_handler: SimulationHandler
    _result_handler: ResultHandler

    def __init__(self):
        self._circuit_handler = CircuitHandler()
        # self._result_handler = ResultHandler()
        self._simulation_handler = SimulationHandler(self._circuit_handler)

    def start_workflow(self, request: UserRequestDto) -> None:
        """
        Manage the simulation workflow.
        
        :param request: User request for the simulation of the configurations
        :type request: UserRequestDto
        """
        # Variable declaration
        schematic_file_path: str = request.circuit_path
        config_params_list: List[ConfigInfoDto] = request.resolve()

        # Initializing the circuit configurations 
        ok = self._circuit_handler.initialize_circuit(request)
        if not ok:
            logger.warning("Initialization failed. Aborting workflow.")
            return None

        # Simulate each configuration one by one
        for config in config_params_list:
            config_number = config.config_number

            if config_number is None:
                raise ValueError("Configuration number cannot be None")
            # Start simulation for this configuration
            self._simulation_handler.start_simulation_process(config_number)

        # Show results summary
        return
