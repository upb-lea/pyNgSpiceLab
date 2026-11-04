"""
Results Handler Module.

This module performs simulation results related task like saving, viewing and analyzing.
"""

# python libraries
import logging
from pathlib import Path

# own libraries
from dtos import SignalSetDto
from ngspice_wrapper import NgspiceWrapper

# 3rd party libraries
import numpy as np
from spicelib import RawRead
from pysignalscope import Scope, Channel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultHandler:
    """Class that handles viewing and analysis of simulation results."""

    _results_dir: Path  # Directory in which the raw result files are stored
    _dialect: str  # Dialect of the simulator that created the raw files (e.g. "ngspice")
    _raws: dict[str, RawRead]  # Opened raw files, keyed by run ID
    _channels: dict[tuple[str, str], Channel]  # Cache of created channels, keyed by (run ID, trace name)

    def __init__(self, results_dir: Path, dialect: str = "ngspice"):
        """
        Initialize the path to the raw files and the member variables of the ResultHandler class.
        :param results_dir: Directory in which the raw result files are stored
        :type results_dir: Path
        :param dialect: Dialect of the simulator that created the raw files
        :type dialect: str
        """
        self._results_dir = Path(results_dir)
        if not self._results_dir.is_dir():
            raise FileNotFoundError(f"Results directory does not exist: '{self._results_dir}'")

        self._dialect = dialect
        self._raws = {}
        self._channels = {}

    def load_run(self, circuit_name: str, config_number: int) -> str:
        """
        Load the raw result file of a configuration.
        :param circuit_name: Name of the original schematic circuit file
        :type circuit_name: str
        :param config_number: Configuration number of the simulated configuration
        :type config_number: int
        :return: Run ID, which is used to request signals of this run
        :rtype: str
        """
        # Run ID follows the naming convention of the result files
        run_id = f"{circuit_name}-config_{config_number}"

        # Open the raw file only once
        if run_id not in self._raws:
            path = self._locate_file(run_id)
            self._raws[run_id] = RawRead(str(path), dialect=self._dialect)

        return run_id

    def list_runs(self) -> list[str]:
        """
        List the run IDs of all loaded runs.
        :return: Run IDs of the loaded runs
        :rtype: list[str]
        """
        return list(self._raws)

    def list_signals(self, run_id: str) -> list[str]:
        """
        List the trace names available in the raw file of a run (without the time axis).
        :param run_id: Run ID returned by load_run
        :type run_id: str
        :return: Trace names available in the run
        :rtype: list[str]
        """
        raw = self._get_raw(run_id)

        return [name for name in raw.get_trace_names() if name.lower() != "time"]

    def get_channel(self, run_id: str, trace_name: str) -> Channel:
        """
        Get a signal of a run as a PySignalScope channel.
        :param run_id: Run ID returned by load_run
        :type run_id: str
        :param trace_name: Trace name as listed by list_signals (e.g. "I(l1)")
        :type trace_name: str
        :return: Channel holding the time axis and the values of the signal
        :rtype: Channel
        """
        raw = self._get_raw(run_id)
        key = (run_id, trace_name)

        # Create the channel only on first request
        if key not in self._channels:
            values = raw.get_trace(trace_name).get_wave()
            time = raw.get_axis()

            self._channels[key] = Scope.from_numpy(
                np.array([time, values], dtype=np.float64),
                mode="time",
                label=f"{trace_name} | {run_id}",
                unit=self._unit_of(trace_name),
            )

        return self._channels[key]

    def get_channels(self, requests: list[tuple[str, str]]) -> list[Channel]:
        """
        Get several signals as PySignalScope channels.
        :param requests: List of (run ID, trace name) pairs
        :type requests: list[tuple[str, str]]
        :return: Channels in the order of the requests
        :rtype: list[Channel]
        """
        return [self.get_channel(run_id, trace_name) for run_id, trace_name in requests]

    def _get_raw(self, run_id: str) -> RawRead:
        """
        Get the opened raw file of a run.
        :param run_id: Run ID returned by load_run
        :type run_id: str
        :return: Opened raw file
        :rtype: RawRead
        """
        if run_id not in self._raws:
            raise RuntimeError(f"Run '{run_id}' is not loaded. Loaded runs: {self.list_runs()}")

        return self._raws[run_id]

    @staticmethod
    def _unit_of(trace_name: str) -> str:
        """
        Derive the unit of a signal from its trace name.
        :param trace_name: Trace name (e.g. "V(vout)" or "I(l1)")
        :type trace_name: str
        :return: "V" for voltages, "A" for currents, otherwise an empty string
        :rtype: str
        """
        prefix = trace_name[:1].upper()

        return {"V": "V", "I": "A"}.get(prefix, "")

    def _locate_file(self, run_id: str) -> Path:
        """
        Build the path of the raw file of a run and check that it exists.
        :param run_id: Run ID, which equals the file name without extension
        :type run_id: str
        :return: File path of the raw file
        :rtype: Path
        """
        path = self._results_dir / f"{run_id}.raw"
        if not path.is_file():
            raise FileNotFoundError(f"Result file not found: '{path}'")

        return path