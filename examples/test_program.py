"""
User Program.

This program sets the user requirements and follows the simulation of the circuit configurations
"""
# python libraries
from pathlib import Path

# 3rd party libraries
from pysignalscope import Scope

# own libraries
from pyngspicelab import ConfigInfoDto, UserRequestDto, SessionHandler, ResultHandler

# Project root folder path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Circuit files path
CIRCUIT_DIR = PROJECT_ROOT / "examples" / "user_defined_circuits"

# Component model library path
LIBRARY_DIR = PROJECT_ROOT / "examples" / "libraries"

# User request declaration
request = UserRequestDto(

    # Main schematic file path for a circuit topology
    # Replace the path to the test circuit here
    # Also replace the path to the library in the test_circuit.cir (currently not required as circuit is adapted with all libraries)
    circuit_path=str(CIRCUIT_DIR / "test_circuit.cir"),

    # Mapping of library names to library paths and sub circuit definitions
    library_map={
        "GA_org": {
            "path": str(LIBRARY_DIR / "GaN_PSpice_GS61008T_L1V4P1_ASA.lib"),
            "subckt": "D G S G GaN_PSpice_GS61008T_L1V4P1"
        },
        "GA_changed": {
            "path": str(LIBRARY_DIR / "GaN_PSpice_GS61008T_L1V4P1_ASA_CHG.lib"),
            "subckt": "D G S G GaN_PSpice_GS61008T_L1V4P1_CHG"
        },
        "GA_EPC": {
            "path": str(LIBRARY_DIR / "EPC2212_V1_PSPICE.net"),
            "subckt": "G D S  EPC2212"
        }
    },

    # Circuit configuration parameters list
    configurations=[
        ConfigInfoDto(
            config_parameters={"rload": "5.8", "C2": "1.5u", "R1": "5.1"},
            config_libraries={"XQ1": "GA_org", "XQ2": "GA_org", "XQ3": "GA_org", "XQ4": "GA_org", "XQ5": "GA_org"},
            voltage_sources={"VHS1": "PULSE(0 6 40n 2n 2n 1.739290u 3.486580u)", "VLS1": "PULSE(0 6 1.803290u 2n 2n 1.703290u 3.486580u)"},
            sim_time_step="50n",
            sim_time="100u"
        ),
        ConfigInfoDto(
            config_parameters={"rLoad": "5.8", "C2": "1.5u", "R1": "5.1"},
            config_libraries={"XQ1": "GA_changed", "XQ2": "GA_changed", "XQ3": "GA_changed", "XQ4": "GA_changed", "XQ5": "GA_changed"},
            voltage_sources={"VHS1": "PULSE(0 6 40n 2n 2n 1.739290u 3.486580u)", "VLS1": "PULSE(0 6 1.803290u 2n 2n 1.703290u 3.486580u)"},
            sim_time_step="50n",
            sim_time="100u"
        )
        # ConfigInfoDto(
        #     config_parameters={"RLoAd": "25", "C2": "10u"},
        #     config_libraries={"XQ1": "GA_org", "XQ2": "GA_org", "XQ3": "GA_org", "XQ4": "GA_org", "XQ5": "GA_org"},
        #     voltage_sources={"VHS1": "PULSE(0 6 40n 2n 2n 789n 3.33u)", "VLS1": "PULSE(0 6 873n 2n 2n 2453n 3.33u)"},
        #     sim_time_step="50n",
        #     sim_time="100u"
        # )
    ]
)

"""Main workflow program"""

session = SessionHandler()
session.start_workflow(request)

# View results of completed simulations
results_path = PROJECT_ROOT / "results"
results_path.mkdir(parents=True, exist_ok=True)
handler = ResultHandler(results_path)

a = handler.load_run("test_circuit", 1)
b = handler.load_run("test_circuit", 2)

print(handler.list_signals(a))     # the user sees what exists, then chooses
print(handler.list_signals(b))     # may differ from run a

channels = handler.get_channels([(a, "V(dc_1)"), (a, "V(load)"), (a, "I(@L1[i])"), (b, "V(dc_1)"), (b, "V(load)")])
Scope.plot_channels(channels)
