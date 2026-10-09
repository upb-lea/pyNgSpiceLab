"""
Session Handler Module.

This module controls the main program flow and handles all the administrative workflows. 
It communicates with other modules such as Circuit Handler, Simulation Handler, etc
"""

# python libraries
import logging
from typing import List

# own libraries
from dtos import ConfigInfoDto, UserRequestDto
from circuit_handler import CircuitHandler
from simulation_handler import SimulationHandler
from result_handler import ResultHandler

# 3rd party libraries


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionHandler:
    """Class that handles the administrative processes of the toolbox."""

    _circuit_handler: CircuitHandler
    _simulation_handler: SimulationHandler
    _result_handler: ResultHandler

    def __init__(self):
        self._circuit_handler = CircuitHandler()
        self._result_handler = ResultHandler()
        self._simulation_handler = SimulationHandler(self._circuit_handler, self._result_handler)

    def start_workflow(self, request: UserRequestDto) -> None:
        """
        Define main workflow process.
        
        :param request: User request for the simulation of the configurations
        :type request: UserRequestDto
        """
        # Variable declaration
        schematic_file_path: str = request.circuit_path
        config_params_list: List[ConfigInfoDto] = request.configurations

        # Initializing the circuit configurations 
        ok = self._circuit_handler.initialize_circuit(schematic_file_path, config_params_list)
        if not ok:
            logger.warning("Initialization failed. Aborting workflow.")
            return None

        # Simulate each configuration one by one
        for config in config_params_list:
            config_number = config.config_number

            # Start simulation for this configuration
            self._simulation_handler.start_simulation_process(config_number)

        # Show results summary
        return None


if __name__ == "__main__":

    request = UserRequestDto()

    # Main schematic file path for a circuit topology
    # Replace the path to the test circuit here
    # Also replace the path to the library in the test_circuit.cir
    request.circuit_path = "prototype_v1/circuit_files/test_circuit.cir"

    # Circuit configuration parameters list
    request.configurations = [
        ConfigInfoDto(
            config_number=1,
            config_parameters={"R1": "1k", "C1": "100u"},
            config_path=request.circuit_path,
            sim_type="tran",
            sim_time_step="10u",
            sim_time="3m"
        ),
        ConfigInfoDto(
            config_number=2,
            config_parameters={"R1": "2k", "C1": "200u"},
            config_path=request.circuit_path,
            sim_type="tran",
            sim_time_step="10u",
            sim_time="3m"
        )
    ]

    """Main workflow program"""

    session = SessionHandler()
    session.start_workflow(request)
