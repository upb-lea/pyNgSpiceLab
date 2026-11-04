"""
Circuit configuration DTOs (Data Transfer Objects).

All circuit and simulation related DTOs 
"""

# python libraries
from dataclasses import dataclass, field
from typing import Dict, List

# own libraries

# 3rd party libraries
import numpy as np

@dataclass
class ConfigInfoDto:
    """Contains circuit configuration information."""

    circuit_name: str  # name of the original schematic circuit file
    config_number: int
    config_parameters: Dict[str, str]
    config_path: str  # adapted schematic file path with adapter libraries for a configuration
    sim_type: str  # simulation type: Operating point, Transient
    sim_time_step: str  # simulation time step with units
    sim_time: str  # simulation total time with units

@dataclass
class UserRequestDto:
    """Contains configuration information given by the user."""

    circuit_path: str = ""  # main schematic file path for a circuit topology
    configurations: List[ConfigInfoDto] = field(default_factory=list)

@dataclass
class SignalSetDto:
    """Neutral representation of the one time-series signal."""

    circuit_name: str  # name of the original schematic circuit file
    config_number: int
    signals: dict[str, np.ndarray]  # name of the signal
    units: dict[str, str]  # unit of the signal
    time: np.ndarray
