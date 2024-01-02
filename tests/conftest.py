import os
import shutil
import tempfile
from pathlib import Path

import pytest
import toml

from pypsse.project import Project

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


@pytest.fixture()
def build_temp_project():
    if os.path.exists(TMP_FOLDER):
        shutil.rmtree(TMP_FOLDER)

    os.mkdir(TMP_FOLDER)
    settings = PROJECT_CREATION_SETTINGS
    s_settings = toml.load(settings["simulation_file"]) if settings["simulation_file"] else {}
    e_settings = toml.load(settings["export_settings_file"]) if settings["export_settings_file"] else {}
    # TODO: Validate settings
    a = Project()
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

    yield
    # if os.path.exists(TMP_FOLDER):
    #     shutil.rmtree(TMP_FOLDER)
