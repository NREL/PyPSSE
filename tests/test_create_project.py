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


# def test_run_sim_static(build_temp_project):
#     project_path = Path(TMP_FOLDER) / PROJECT_NAME
#     file_Path = project_path / SIMULATION_SETTINGS_FILENAME

#     if file_Path.exists():
#         x = Simulator.from_setting_files(file_Path)
#         x.init()
#         x.run()
#     else:
#         msg = f"'{file_Path}' is not a valid path."
#         raise Exception(msg)


def test_run_sim_dynamic(build_temp_project):
    project_path = Path(TMP_FOLDER) / PROJECT_NAME
    file_Path = project_path / SIMULATION_SETTINGS_FILENAME

    if file_Path.exists():
        settings = load_settings(file_Path, project_path)
        settings.simulation.simulation_mode = SimulationModes.DYNAMIC
        settings.simulation.use_profile_manager = False
        settings.helics.cosimulation_mode = False
        x = Simulator(settings)
        x.init()
        x.run()
    else:
        msg = f"'{file_Path}' is not a valid path."
        raise Exception(msg)


# def test_license_availability(_cleanup):
#     example_path = ".tests/examples/static_example"
#     export_path = os.path.join(example_path, "Exports")
#     python_path = sys.executable
#     cmd = rf"{python_path} tests\check_license.py {example_path}"
#     os.system(cmd)
#     assert len(os.listdir(export_path)) > 0, "Example failed to run license not available"
