"""
User Program.

This program sets the user requirements and follows the simulation of the circuit configurations
"""
# python libraries
from pathlib import Path

# 3rd party libraries
from pysignalscope import Scope

# own libraries
from dtos import ConfigInfoDto, UserRequestDto
from ngspice_ctl import SessionHandler
from result_handler import ResultHandler

# User request declaration
request = UserRequestDto(

    # Main schematic file path for a circuit topology
    # Replace the path to the test circuit here
    # Also replace the path to the library in the test_circuit.cir (currenctly not required as circuit is adapted with all libraries)
    circuit_path="prototype_v1/circuit_files/test_circuit.cir",

    # Mapping of library names to library paths and subcircuit definitions
    library_map={
        "GA_org": {
            "path": "prototype_v1/circuit_files/GaN_PSpice_GS61008T_L1V4P1_ASA.lib",
            "subckt": "D G S G GaN_PSpice_GS61008T_L1V4P1"
        },
        "GA_changed": {
            "path": "prototype_v1/circuit_files/GaN_PSpice_GS61008T_L1V4P1_ASA_CHG.lib",
            "subckt": "D G S G GaN_PSpice_GS61008T_L1V4P1_CHG"
        },
        "GA_EPC": {
            "path": "prototype_v1/circuit_files/EPC2212_V1_PSPICE.net",
            "subckt": "G D S  EPC2212"
        }
    },

    # Circuit configuration parameters list
    configurations=[
        ConfigInfoDto(
            config_parameters={"rload": "5.8", "C2": "1.5u", "R1": "10"},
            config_libraries={"Q1": "GA_org", "Q2": "GA_changed", "Q3": "GA_EPC", "Q4": "GA_org", "Q5": "GA_org"},
            sim_time_step="1u",
            sim_time="100u"
        ),
        ConfigInfoDto(
            config_parameters={"RlOad": "25", "C2": "10u"},
            config_libraries={"Q1": "GA_org", "Q2": "GA_changed", "Q3": "GA_EPC", "Q4": "GA_EPC", "Q5": "GA_changed"},
            sim_time_step="1u",
            sim_time="100u"
        )
    ]
)

"""Main workflow program"""

session = SessionHandler()
session.start_workflow(request)

# View results of completed simulations
results_path = Path(r"/home/tatsat/whb/github/pyNgSpiceLab/results")
handler = ResultHandler(results_path)

a = handler.load_run("test_circuit", 1)
b = handler.load_run("test_circuit", 2)

# print(handler.list_signals(a))     # the user sees what exists, then chooses
# print(handler.list_signals(b))     # may differ from run a

channels = handler.get_channels([(a, "V(dc_1)"), (a, "V(load)"), (b, "V(dc_1)"), (b, "V(load)"), (a, "I(@rload[i])")])
Scope.plot_channels(channels)
