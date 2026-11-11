"""
Simulation Handler Module.

This module performs the loading of the circuit into the ngspice. It also alters the values of components based on the configurations.
Finally, it handles the simulation runs.
"""

# python libraries
import logging
from pathlib import Path

# 3rd party libraries

# own libraries
from circuit_handler import CircuitHandler
from ngspice_wrapper import NgspiceWrapper

# configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimulationHandler:
    """Class that handles simulation runs and communications with ngspice_wrapper library."""

    _circuit_handler: CircuitHandler  # CircuitHandler object allowing communication with CircuitHandler module
    _ngspice: NgspiceWrapper  # NgspiceWrapper object allowing communication with ngspice_wrapper library

    def __init__(self, circuit_handler: CircuitHandler):
        """Initialize the member variables of the SimulationHandler class."""
        self._circuit_handler = circuit_handler
        self._ngspice = NgspiceWrapper()

        # Create a 'results' directory in the current working directory.
        self._result_directory = Path.cwd() / "results"
        self._result_directory.mkdir(parents=True, exist_ok=True)

    def start_simulation_process(self, config_number: int) -> None:
        """
        Simulate a configuration with the given configuration number.
        
        :param config_number: Configuration number of the configuration for which simulation is required
        :type config_number: int
        """
        logger.info(f"Starting simulation process for config_number: {config_number}")

        # Communicate with CircuitHandler for configuration information
        config_info = self._circuit_handler.get_circuit_info(config_number)

        if config_info is None:
            logger.info("Configuration does not exist.")
            return

        # Set PSpice behavior to avoid file path case sensitivity issue
        self._ngspice.command("set ngbehavior=ps")

        # Source configuration schematic file path (Load the schematic into ngspice)
        if config_info.config_path is None:
            raise ValueError("Configuration path cannot be None")
        self._ngspice.source_file(config_info.config_path)

        # Alter parameters dynamically in memory of ngspice
        self._ngspice.alter(config_info.config_parameters)

        # The following line is to check that alter command works
        self._ngspice.command("show rload")
        self._ngspice.command("show c2")
        self._ngspice.command("listing")

        # Setup transient simulation command
        tran_cmd = f"{config_info.sim_type} {config_info.sim_time_step} {config_info.sim_time}"

        # Run in background
        self._ngspice.run_background()
        self._ngspice.wait_until_done()

        # Perfom transient simulation
        self._ngspice.command(tran_cmd)

        # Save simulation results in a raw file
        if config_info.circuit_name is None:
            raise ValueError("Configuration path cannot be None")
        raw_result = self._save_raw_file(config_info.circuit_name, config_number)
        logger.info(f"Results saved to: {raw_result}")

    def _save_raw_file(self, circuit_name: str, config_number: int) -> Path:
        """
        Save raw file of the immediate simulation by communicating with ngspice.
        
        :param circuit_name: Name of the original schematic circuit file
        :type circuit_name: str
        :param config_number: Configuration number of the configuration whose simulation is completed
        :type config_number: int
        :return: File path of the save result
        :rtype: Path
        """
        # File path variable defining the naming convention of result files
        raw_file = (self._result_directory / f"{circuit_name}-config_{config_number}.raw")

        # Communicate with ngspice_wrapper library to write results to raw file
        self._ngspice.command(f"write {raw_file}")

        return Path(raw_file)
