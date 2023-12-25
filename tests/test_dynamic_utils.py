import os
import tempfile

from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.simulator import Simulator

PROJECT_CREATION_SETTINGS = {
    "simulation_file": None,
    "export_settings_file": None,
    "psse_project_folder": "./tests/data/psse_project",
    "profile_store": "./tests/data/profiles/Profiles.hdf5",
    "profile_mapping": "./tests/data/profiles/Profile_mapping.toml",
    "overwrite": True,
    "autofill": True,
}

TEMPPATH = tempfile.gettempdir()
TMP_FOLDER = os.path.join(TEMPPATH, "temp")
PROJECT_NAME = "psse_project"

base_path = os.getcwd()
dynamic_project_path = os.path.join(os.path.dirname(base_path), "examples", "dynamic_example")


def test_run_sim_dynamic_save_model():
    path = os.path.join(dynamic_project_path, "Settings", SIMULATION_SETTINGS_FILENAME)
    if os.path.exists(path):
        x = Simulator(path)
        x.init()
        x.save_model()
        x.run()
    else:
        msg = f"'{path}' is not a valid path."
        raise Exception(msg)


def test_run_sim_dynamic_break_model():
    path = os.path.join(dynamic_project_path, "Settings", SIMULATION_SETTINGS_FILENAME)
    if os.path.exists(path):
        x = Simulator(path)
        x.init()
        x.sim.break_loads(
            [
                {"bus": 153, "id": "1"},
            ]
        )
        x.run()
    else:
        msg = f"'{path}' is not a valid path."
        raise Exception(msg)
