"""
Circuit configuration DTOs (Data Transfer Objects).

All circuit and simulation related DTOs 
"""

# python libraries
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

# 3rd party libraries
import numpy as np

# own libraries

@dataclass
class ConfigInfoDto:
    """Contains circuit configuration information."""

    # These fields are the typically provided by the user
    config_parameters: Dict[str, str]
    config_libraries: Dict[str, str]  # e.g., {"Transistor1": "GA_org", "Transistor2": "GA_CHG"}
    sim_time_step: str  # simulation time step with units
    sim_time: str  # simulation total time with units

    # These fields are optional for the user; they will be auto-filled
    circuit_name: Optional[str] = None  # name of the original schematic circuit file
    config_number: Optional[int] = None
    config_path: Optional[str] = None  # adapted schematic file path with adapter libraries for a configuration
    
    sim_type: Optional[str] = "tran"  # simulation type: Currently only supports 'Transient'

@dataclass
class UserRequestDto:
    """Contains configuration information given by the user."""

    circuit_path: str = ""  # main schematic file path for a circuit topology
    library_map: dict[str, dict[str, str]] = field(default_factory=dict)  # A mapping of library names to its paths and subcircuit definitions
    configurations: List[ConfigInfoDto] = field(default_factory=list)

    def resolve(self) -> List[ConfigInfoDto]:
        """Automatically fills in the missing fields for each ConfigInfoDto."""
        circuit_file = Path(self.circuit_path)
        circuit_name = circuit_file.stem  # e.g., "voltage_divider.cir" -> "voltage_divider"

        for idx, config in enumerate(self.configurations, start=1):
            # Only fill in if the user has not overidden manually
            if not config.circuit_name:
                config.circuit_name = circuit_name
            if config.config_number is None:
                config.config_number = idx
            if not config.config_path:
                config.config_path = str(circuit_file)

        return self.configurations

@dataclass
class SignalSetDto:
    """Neutral representation of the one time-series signal."""

    circuit_name: str  # name of the original schematic circuit file
    config_number: int
    signals: dict[str, np.ndarray]  # name of the signal
    units: dict[str, str]  # unit of the signal
    time: np.ndarray
