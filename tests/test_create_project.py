import os
import sys
import toml
import pytest
import tempfile
from pypsse.pypsse_project import pypsse_project
from pypsse.pypsse_instance import pyPSSE_instance
from pypsse.common import SIMULATION_SETTINGS_FILENAME

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
        err = os.system('rmdir /S /Q "{}"'.format(TMP_FOLDER))
        assert err == 0, "Error removing temporary project folder"
    yield
    if os.path.exists(TMP_FOLDER):
        err = os.system('rmdir /S /Q "{}"'.format(TMP_FOLDER))
        assert err == 0, "Error removing temporary project folder"

def test_create_project(cleanup):
    os.mkdir(TMP_FOLDER)
    settings = PROJECT_CREATION_SETTINGS
    sSettings = toml.load(settings['simulation_file']) if settings['simulation_file'] else {}
    eSettings = toml.load(settings['export_settings_file']) if settings['export_settings_file'] else {}
    # TODO: Validate settings
    a = pypsse_project()
    a.create(
        TMP_FOLDER,
        PROJECT_NAME,
        settings['psse_project_folder'],
        sSettings,
        eSettings,
        settings['profile_store'],
        settings['profile_mapping'],
        settings['overwrite'],
        settings['autofill']
    )
    return

def test_run_sim_static(cleanup):
    test_create_project(None)
    path = os.path.join(TMP_FOLDER, PROJECT_NAME, "Settings", SIMULATION_SETTINGS_FILENAME)
    if os.path.exists(path):
        x = pyPSSE_instance(path)
        x.init()
        x.run()
    else:
        raise Exception(f"'{path}' is not a valid path.")
    return

def test_run_sim_dynamic(cleanup):
    test_create_project(None)
    path = os.path.join(TMP_FOLDER, PROJECT_NAME, "Settings", SIMULATION_SETTINGS_FILENAME)
    sSettings = toml.load(path)
    sSettings["Simulation"]["Simulation mode"] = "Dynamic"
    sSettings["Simulation"]["Use profile manager"] = False
    with open(path, 'w') as f:
        toml.dump(sSettings, f)
    if os.path.exists(path):
        x = pyPSSE_instance(path)
        x.init()
        x.run()
    else:
        raise Exception(f"'{path}' is not a valid path.")
    return

def test_license_availability(cleanup):
    example_path = "./examples/static_example"
    export_path = os.path.join(example_path, "Exports")
    python_path = sys.executable
    cmd = f'{python_path} tests\check_license.py {example_path}'
    reply = os.system(cmd)
    assert len(os.listdir(export_path)) > 0, "Example failed to run license not available"
    return