import os
import toml
import tempfile
import shutil
import pytest
from pypsse.pyPSSE_project import pyPSSE_project

PROJECT_CREATION_SETTINGS = {
        "simulation_file": None,
        "export_settings_file": None,
        "project": 'pypsse_test_project',
        "psse_project_folder": "./tests/data/psse_project",
        "profile_store": "./tests/data/profiles/Profiles.hdf5",
        "profile_mapping": "./tests/data/profiles/Profile_mapping",
        "overwrite": True,
        "autofill": True,
    }

TEMPPATH = tempfile.gettempdir()
PATH = os.path.join(TEMPPATH, "test_project_psse")
@pytest.fixture
def pypsse_project():
    if os.path.exists(PATH):
        shutil.rmtree(PATH)
    yield
    if os.path.exists(PATH):
        shutil.rmtree(PATH)


def test_create_project():
    settings = PROJECT_CREATION_SETTINGS
    sSettings = toml.load(settings['simulation_file']) if settings['simulation_file'] else {}
    eSettings = toml.load(settings['export_settings_file']) if settings['export_settings_file'] else {}
    # TODO: Validate settings
    a = pyPSSE_project()
    a.create(
        PATH,
        settings['project'],
        settings['psse_project_folder'],
        sSettings,
        eSettings,
        settings['profile_store'],
        settings['profile_mapping'],
        settings['overwrite'],
        settings['autofill']
    )
    return
