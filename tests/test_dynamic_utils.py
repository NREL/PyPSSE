import os
import tempfile
from pathlib import Path

from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.enumerations import SimulationModes
from pypsse.simulator import Simulator
from pypsse.utils.utils import load_settings

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

def load_dynamic_model():
    global counter
    project_path = Path(TMP_FOLDER) / PROJECT_NAME
    file_Path = project_path / SIMULATION_SETTINGS_FILENAME

    if file_Path.exists():
        settings = load_settings(file_Path, project_path)
        settings.simulation.simulation_mode = SimulationModes.DYNAMIC
        settings.simulation.use_profile_manager = False
        settings.helics.cosimulation_mode = False
        
        x = Simulator(settings)
        x.init()
        yield x
        x.force_psse_halt()
    else:
        msg = f"'{file_Path}' is not a valid path."
        raise Exception(msg)


def test_run_sim_dynamic_save_model(build_temp_project):
   
    x = load_dynamic_model()
    for simulator in x:
        files = simulator.sim.save_model()
        for file in files:
            assert file.exists(), f"{file!s}"


def test_disable_generation(build_temp_project):
    x = load_dynamic_model()
    for simulator in x:
        ...
    


# def test_disbale_load_model(build_temp_project):
#     x = load_dynamic_model()
#     x = next(x)


# def test_channel_setup(build_temp_project):
#     x = load_dynamic_model()
#     x = next(x)


# def test_load_break(build_temp_project):
#     x = load_dynamic_model()
#     x = next(x)
