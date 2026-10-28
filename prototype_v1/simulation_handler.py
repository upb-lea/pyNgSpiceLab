"""
Simulation Handler Module.

This module performs the loading of the circuit into the ngspice. It also alters the values of components based on the configurations.
Finally, it handles the simulation runs.
"""

# python libraries
import logging

# own libraries
from circuit_handler import CircuitHandler
from result_handler import ResultHandler
from ngspice_wrapper import NgspiceWrapper

# 3rd party libraries


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimulationHandler:
    """Class that handles simulation runs and communications with ngspice_wrapper library."""

    _circuit_handler: CircuitHandler  # CircuitHandler object allowing communication with CircuitHandler module
    _result_handler: ResultHandler
    _ngspice: NgspiceWrapper  # NgspiceWrapper object allowing communication with ngspice_wrapper library

    def __init__(self, circuit_handler: CircuitHandler, result_handler: ResultHandler):
        """Initialize the member variables of the SimulationHandler class."""
        self._circuit_handler = circuit_handler
        self._result_handler = result_handler
        self._ngspice = NgspiceWrapper()

    def start_simulation_process(self, config_number: int) -> None:
        """
        Simulate a configuration with the given configuration number.
        
        :param config_number: Configuration number of the configuration for which simulation is required
        :type config_number: int
        """
        logger.info(f"Starting simulation process for config_number: {config_number}")

        # Communicate with CircuitHandler for configuration information
        config_info = self._circuit_handler.get_circuit_info(config_number)

        # Set PSpice behavior to avoid file path case sensitivity issue
        self._ngspice.command("set ngbehavior=ps")

        # Source configuration schematic file path (Load the schematic into ngspice)
        self._ngspice.source_file(config_info.config_path)

        # Alter parameters dynamically in memory of ngspice
        self._ngspice.alter(config_info.config_parameters)

        # The following line is to check that alter command works
        self._ngspice.command("show r1")
        self._ngspice.command("show c1")

        # Setup transient simulation command
        tran_cmd = f"{config_info.sim_type} {config_info.sim_time_step} {config_info.sim_time}"

        # Run in background
        self._ngspice.run_background()
        self._ngspice.wait_until_done()

        # Perfom transient simulation
        self._ngspice.command(tran_cmd)

        # Save simulation results in a raw file
        raw_result = self._result_handler.save_raw_file(config_number, self._ngspice)
        logger.info(f"Results saved to: {raw_result}")
