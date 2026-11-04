"""
Minimal ctypes wrapper around libngspice.so (the official ngspice shared-library API).

Reference: https://ngspice.sourceforge.io/shared.html
"""
import ctypes
from ctypes import (
    c_char_p, c_int, c_bool, c_void_p, c_double, c_short,
    CFUNCTYPE, POINTER, Structure
)
import numpy as np
import time
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# vecvalues / vecvaluesall structs (matches ngspice/sharedspice.h)
# These are what SendData hands you on every timestep during bg_run.
# ---------------------------------------------------------------------------
class vecvalues(Structure):
    """Represent a single ngspice vector value."""

    _fields_ = [
        ("name", c_char_p),
        ("creal", c_double),
        ("cimag", c_double),
        ("is_scale", c_bool),
        ("is_complex", c_bool),
    ]


class vecvaluesall(Structure):
    """Represent the collection of vector values sent by ngspice."""

    _fields_ = [
        ("veccount", c_int),
        ("vecindex", c_int),
        ("vecsa", POINTER(POINTER(vecvalues))),
    ]


# ---------------------------------------------------------------------------
# Callback signatures required by ngSpice_Init
# ---------------------------------------------------------------------------
SendChar = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
SendStat = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
ControlledExit = CFUNCTYPE(c_int, c_int, c_bool, c_bool, c_int, c_void_p)
SendData = CFUNCTYPE(c_int, POINTER(vecvaluesall), c_int, c_int, c_void_p)
SendInitData = CFUNCTYPE(c_int, c_void_p, c_int, c_void_p)
BGThreadRunning = CFUNCTYPE(c_int, c_bool, c_int, c_void_p)


# ---------------------------------------------------------------------------
# vector_info struct (matches ngspice/sharedspice.h) - used for post-hoc reads
# ---------------------------------------------------------------------------
class vector_info(Structure):
    """Represent metadata and data storage for an ngspice vector."""

    _fields_ = [
        ("v_name", c_char_p),
        ("v_type", c_int),
        ("v_flags", c_short),
        ("v_realdata", POINTER(c_double)),
        ("v_compdata", c_void_p),   # ncomplex*, unused here
        ("v_length", c_int),
    ]


class NgspiceWrapper:
    """
    Thin wrapper around libngspice.so.

    Usage:
        ng = NgSpiceShared()
        ng.load_circuit(["V1 1 0 DC 5", "R1 1 0 1k", ".op", ".end"])
        ng.command("tran 1u 1m")
        t = ng.get_vector("time")
        v = ng.get_vector("v(1)")
    """

    def __init__(self, lib_name: str = "libngspice.so", verbose: bool = True,
                 on_data: Callable[[dict[str, float], int], None] | None = None):
        """
        Initialize the ngspice shared-library interface.

        on_data: optional callable(dict[str, float], step_index: int) invoked
                 on every timestep while a simulation is running in the
                 background (bg_run). Receives the current real value of
                 every vector, keyed by name (e.g. 'V(1)', 'time').
        """
        self.verbose = verbose
        self._on_data_user_cb = on_data
        self._bg_finished = False
        self._lib = ctypes.CDLL(lib_name)

        # keep references so they aren't garbage-collected
        self._cb_send_char = SendChar(self._on_send_char)
        self._cb_send_stat = SendStat(self._on_send_char)
        self._cb_exit = ControlledExit(self._on_exit)
        self._cb_send_data = SendData(self._on_send_data)
        self._cb_send_init = SendInitData(lambda *a: 0)
        self._cb_bg_running = BGThreadRunning(self._on_bg_running)

        self._lib.ngSpice_Init.argtypes = [
            SendChar, SendStat, ControlledExit, SendData, SendInitData,
            BGThreadRunning, c_void_p,
        ]
        self._lib.ngSpice_Init.restype = c_int

        rc = self._lib.ngSpice_Init(
            self._cb_send_char, self._cb_send_stat, self._cb_exit,
            self._cb_send_data, self._cb_send_init, self._cb_bg_running, None,
        )
        if rc != 0:
            raise RuntimeError(f"ngSpice_Init failed with code {rc}")

        self._lib.ngSpice_Command.argtypes = [c_char_p]
        self._lib.ngSpice_Command.restype = c_int

        self._lib.ngSpice_Circ.argtypes = [POINTER(c_char_p)]
        self._lib.ngSpice_Circ.restype = c_int

        self._lib.ngGet_Vec_Info.argtypes = [c_char_p]
        self._lib.ngGet_Vec_Info.restype = POINTER(vector_info)

        self._lib.ngSpice_AllVecs.argtypes = [c_char_p]
        self._lib.ngSpice_AllVecs.restype = POINTER(c_char_p)

        self._lib.ngSpice_CurPlot.restype = c_char_p

        self._lib.ngSpice_running.argtypes = []
        self._lib.ngSpice_running.restype = c_bool

    # -- callbacks -----------------------------------------------------
    def _on_send_char(self, message, ident, user_data):
        if self.verbose and message:
            print(message.decode(errors="ignore"))
        return 0

    def _on_exit(self, exit_status, immediate, quit_ng, ident, user_data):
        # Prevent ngspice from calling exit() on the whole Python process
        return exit_status

    def _on_send_data(self, vecvaluesall_ptr, numvecs, ident, user_data):
        """Handle vector data received from ngspice during bg_run."""
        vda = vecvaluesall_ptr.contents
        values = {}
        for i in range(vda.veccount):
            vv = vda.vecsa[i].contents
            name = vv.name.decode() if vv.name else f"vec{i}"
            values[name] = vv.creal
        if self._on_data_user_cb is not None:
            self._on_data_user_cb(values, vda.vecindex)
        return 0

    def _on_bg_running(self, is_running, ident, user_data):
        # Called when the background thread finishes (is_running goes False)
        if not is_running:
            self._bg_finished = True
        return 0

    # -- public API ------------------------------------------------------
    def command(self, cmd: str) -> int:
        """
        Send a raw ngspice command, e.g. 'tran 1u 1m' or 'alter r1=2k'.

        :param cmd: Raw ngspice command to execute.
        """
        return int(self._lib.ngSpice_Command(cmd.encode()))

    def run_background(self) -> int:
        """
        Start the simulation in a background thread and return immediately.

        Values stream to the on_data callback as they're computed.
        """
        self._bg_finished = False
        return self.command("bg_run")

    def running(self) -> bool:
        """Return whether a background ngspice simulation is running."""
        return bool(self._lib.ngSpice_running())

    def wait_until_done(self, poll_interval: float = 0.05) -> None:
        """
        Block until the background run finishes (polls ngSpice_running).

        :param poll_interval: Time in seconds between running-state checks.
        """
        # small startup grace period so ngSpice_running() has time to flip True
        time.sleep(poll_interval)
        while self.running():
            time.sleep(poll_interval)

    def load_circuit(self, lines: list[str]) -> int:
        """
        Load a netlist from a list of strings (no leading/trailing .end needed check).

        :param lines: Netlist lines to load into ngspice.
        """
        arr_type = c_char_p * (len(lines) + 1)
        arr = arr_type(*[line.encode() for line in lines], None)
        return int(self._lib.ngSpice_Circ(arr))

    def current_plot(self) -> str:
        """Return the name of the current ngspice plot."""
        cp = self._lib.ngSpice_CurPlot()
        return str(cp.decode()) if cp else ""

    def all_vector_names(self, plot: str | None = None) -> list[str]:
        """
        Return the names of all vectors available in the specified plot.

        :param plot: Name of the ngspice plot to inspect.
        """
        plot = plot or self.current_plot()
        ptr = self._lib.ngSpice_AllVecs(plot.encode())
        names = []
        i = 0
        while ptr[i]:
            names.append(ptr[i].decode())
            i += 1
        return names

    def get_vector(self, name: str) -> np.ndarray:
        """
        Fetch a result vector (e.g. 'time', 'v(1)', 'i(v1)') as a numpy array.

        :param name: Name of the ngspice vector to retrieve.
        """
        info_ptr = self._lib.ngGet_Vec_Info(name.encode())
        if not info_ptr:
            raise KeyError(f"No such vector: {name!r}. \n Available: {self.all_vector_names()}")
        info = info_ptr.contents
        length = info.v_length
        if not info.v_realdata:
            raise ValueError(f"Vector {name!r} has no real data (complex only?)")
        data = np.ctypeslib.as_array(info.v_realdata, shape=(length,)).copy()
        return data

    def stop(self):
        """Stop a running background simulation."""
        return self.command("bg_halt")

    # -- Additions to NgSpiceShared class --------------------------------

    def alter(self, parameters: dict[str, str]) -> None:
        """
        Alters circuit element values or model parameters dynamically.

        Args:
            parameters: Dictionary of parameters to alter,
                        e.g., {"R1": "2k", "V1": 5.0, "M1[W]": "10u"}
        """
        for param_name, val in parameters.items():
            # Constructs and sends: alter <param_name> = <val>
            cmd = f"alter {param_name} = {val}"
            rc = self.command(cmd)
            if rc != 0 and self.verbose:
                print(f"[Warning] Failed to alter parameter: {cmd} (code {rc})")

    def source_file(self, file_path: str) -> int:
        """
        Load an ngspice circuit or command file from the specified path.

        :param file_path: Path to the ngspice circuit or command file.
        """
        path = Path(file_path).expanduser().resolve()
        return self.command(f"source {path}")
