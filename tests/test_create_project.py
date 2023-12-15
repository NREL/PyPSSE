import os
import shutil
import sys
import tempfile

import pytest
import toml

from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.project import pypsse_project
from pypsse.Simulator import Simulator

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


@pytest.fixture
def cleanup():
    if os.path.exists(TMP_FOLDER):
        shutil.rmtree(TMP_FOLDER)
    yield
    if os.path.exists(TMP_FOLDER):
        shutil.rmtree(TMP_FOLDER)


def test_create_project(cleanup):
    os.mkdir(TMP_FOLDER)
    settings = PROJECT_CREATION_SETTINGS
    s_settings = toml.load(settings["simulation_file"]) if settings["simulation_file"] else {}
    e_settings = toml.load(settings["export_settings_file"]) if settings["export_settings_file"] else {}
    # TODO: Validate settings
    a = pypsse_project()
    a.create(
        TMP_FOLDER,
        PROJECT_NAME,
        settings["psse_project_folder"],
        s_settings,
        e_settings,
        settings["profile_store"],
        settings["profile_mapping"],
        settings["overwrite"],
        settings["autofill"],
    )


def test_run_sim_static(cleanup):
    test_create_project(None)
    path = os.path.join(TMP_FOLDER, PROJECT_NAME, "Settings", SIMULATION_SETTINGS_FILENAME)
    if os.path.exists(path):
        x = Simulator(path)
        x.init()
        x.run()
    else:
        msg = f"'{path}' is not a valid path."
        raise Exception(msg)


def test_run_sim_dynamic(cleanup):
    test_create_project(None)
    path = os.path.join(TMP_FOLDER, PROJECT_NAME, "Settings", SIMULATION_SETTINGS_FILENAME)
    s_settings = toml.load(path)
    s_settings["Simulation"]["Simulation mode"] = "Dynamic"
    s_settings["Simulation"]["Use profile manager"] = False
    with open(path, "w") as f:
        toml.dump(s_settings, f)
    if os.path.exists(path):
        x = Simulator(path)
        x.init()
        x.run()
    else:
        msg = f"'{path}' is not a valid path."
        raise Exception(msg)


def test_license_availability(cleanup):
    example_path = "./examples/static_example"
    export_path = os.path.join(example_path, "Exports")
    python_path = sys.executable
    cmd = rf"{python_path} tests\check_license.py {example_path}"
    os.system(cmd)
    assert len(os.listdir(export_path)) > 0, "Example failed to run license not available"
