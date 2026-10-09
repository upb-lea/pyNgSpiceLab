"""
Results Handler Module.

This module performs simulation results related task like saving, viewing and analyzing.
"""

# python libraries
import logging
from pathlib import Path

# own libraries
from ngspice_wrapper import NgspiceWrapper

# 3rd party libraries


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultHandler:
    """Class that handles saving, viewing and analysis of simulation results."""

    def __init__(self):
        """Create a 'results' directory in the current working directory."""
        self._result_directory = Path.cwd() / "results"
        self._result_directory.mkdir(parents=True, exist_ok=True)

    def save_raw_file(self, config_number: int, ngspice: NgspiceWrapper) -> Path:
        """
        Save raw file of the immediate simulation by communicating with ngspice.
        
        :param config_number: Configuration number of the configuration whose simulation is completed
        :type config_number: int
        :param ngspice: NgspiceWrapper object to allow communication with ngspice_wrapper library
        :type ngspice: NgspiceWrapper
        :return: File path of the save result
        :rtype: Path
        """
        # File path variable declaration
        raw_file = (self._result_directory / f"config_{config_number}.raw")

        # Communicate with ngspice_wrapper library to write results to raw file
        ngspice.command(f"write {raw_file}")

        return Path(raw_file)
