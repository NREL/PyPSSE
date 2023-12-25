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
    project_path = Path(TMP_FOLDER) / PROJECT_NAME
    file_Path = project_path / SIMULATION_SETTINGS_FILENAME

    if file_Path.exists():
        settings = load_settings(file_Path, project_path)
        settings.simulation.simulation_mode = SimulationModes.STATIC
        settings.simulation.use_profile_manager = True
        settings.helics.cosimulation_mode = False
        yield settings
        x = Simulator(settings)
        x.init()
        x.run

    else:
        msg = f"'{file_Path}' is not a valid path."
        raise Exception(msg)


def test_writer_hdf5(build_temp_project):
    settings = next(load_dynamic_model())
    # settings.export.


def test_writer_json(build_temp_project):
    x = load_dynamic_model()
    x = next(x)


def test_writer_csv(build_temp_project):
    x = load_dynamic_model()
    x = next(x)
