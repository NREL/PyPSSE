import json
import logging
import os
from distutils.dir_util import copy_tree
from pathlib import Path
from shutil import copy

import pandas as pd
import toml

from pypsse.common import (
    CASESTUDY_FOLDER,
    DEFAULT_COORDINATES_FILE,
    DEFAULT_EXCEL_FILE,
    DEFAULT_GRAPH_FILE,
    DEFAULT_LOG_FILE,
    DEFAULT_OUT_FILE,
    DEFAULT_OUTX_FILE,
    DEFAULT_PROFILE_MAPPING_FILENAME,
    DEFAULT_SUBSCRIPTION_FILENAME,
    DEFAULTS_FOLDER,
    EXPORTS_SETTINGS_FILENAME,
    PROFILES_FOLDER,
    SIMULATION_SETTINGS_FILENAME,
)
from pypsse.enumerations import SubscriptionFileRequiredColumns
from pypsse.models import ExportFileOptions, ProjectDefination, SimulationSettings
from pypsse.profile_manager.profile_store import ProfileManager


class Project:
    "This class defines the structure of a PyPSSE project"

    def __init__(self):
        logging.root.setLevel("DEBUG")
        self.basepath = Path(__file__).parent

    def create(
        self,
        parent_path,
        project_name,
        psse_folder,
        simulation_settings_file,
        export_settings_file,
        profile_store_file,
        profile_mapping_file,
        overwrite=True,
        autofill=True,
    ):
        "The methods creates a new PyPSSE project"

        exports_dict = toml.load(self.basepath / DEFAULTS_FOLDER / EXPORTS_SETTINGS_FILENAME)
        export_settings = ExportFileOptions(**exports_dict)

        if export_settings_file:
            export_settings_file = Path(export_settings_file)
            assert export_settings_file.exists(), f"Export file '{export_settings_file}' does not exist"
            new_export_settings = toml.load(export_settings_file)
            export_settings.update(**new_export_settings)

        sim_setting_dict = toml.load(self.basepath / DEFAULTS_FOLDER / SIMULATION_SETTINGS_FILENAME)
        simulation_settings = SimulationSettings(**sim_setting_dict)

        if simulation_settings_file:
            simulation_settings_file = Path(simulation_settings_file)
            assert simulation_settings_file.exists(), f"Export file '{simulation_settings_file}' does not exist"
            sim_setting_dict = toml.load(simulation_settings_file)
            simulation_settings.update(**sim_setting_dict)

        simulation_settings.simulation.project_path = Path(parent_path) / project_name

        self.project = ProjectDefination(
            project_name=project_name,
            simulation_settings=simulation_settings,
            export_settings=export_settings,
            overwrite=overwrite,
            autofill=autofill,
        )
        self.project_path = Path(parent_path) / project_name

        self._create_folders()

        if psse_folder:
            psse_files = self._copy_psse_project_files(psse_folder)
            if autofill and psse_files:
                self._autofill_settings(psse_files, profile_store_file, profile_mapping_file)

        self._update_export_files()
        self._write_setting_files()

    def _update_export_files(self):
        self.project.simulation_settings.export.out_file = DEFAULT_OUT_FILE
        self.project.simulation_settings.export.outx_file = DEFAULT_OUTX_FILE
        self.project.simulation_settings.export.log_file = DEFAULT_LOG_FILE
        self.project.simulation_settings.export.excel_file = DEFAULT_EXCEL_FILE
        self.project.simulation_settings.export.coordinate_file = DEFAULT_COORDINATES_FILE
        self.project.simulation_settings.export.networkx_graph_file = DEFAULT_GRAPH_FILE

    def _psse_project_file_dict(self, path):
        "Creates a mapping of all PyPSSE project files"
        file_dict = {}
        for _, _, files in os.walk(path):
            for file in files:
                _, ext = file.split(".")
                if ext not in file_dict:
                    file_dict[ext.lower()] = [file]
                else:
                    file_dict[ext.lower()].append(file)
        return file_dict

    def _copy_psse_project_files(self, psse_folder):
        "Copies PSSE file to the new project folder"
        psse_folder = Path(psse_folder)
        if psse_folder.exists():
            new_path = self.project_path / CASESTUDY_FOLDER
            copy_tree(str(psse_folder.absolute()), str(new_path.absolute()))
            psse_files = self._psse_project_file_dict(new_path)
        else:
            msg = f"PSSE project path does not exist. ({psse_folder}) {os.getcwd()}"
            raise Exception(msg)
        return psse_files

    def _write_setting_files(self):
        sim_file_path = self.project_path / SIMULATION_SETTINGS_FILENAME
        with open(sim_file_path, "w") as f:
            toml.dump(json.loads(self.project.simulation_settings.model_dump_json()), f)

        export_file_path = self.project_path / EXPORTS_SETTINGS_FILENAME
        with open(export_file_path, "w") as f:
            toml.dump(json.loads(self.project.export_settings.model_dump_json()), f)

    def _create_folders(self):
        "Creates folder structure for a new project. Older project can be over-written"

        for folder in self.project.project_folders:
            project_folder = self.project_path / folder.value
            if project_folder.exists() and not self.project.overwrite:
                msg = "Project folder already exists. Set overwrite=true to overwrite existing projects"
                raise Exception(msg)
            elif not project_folder.exists():
                project_folder.mkdir(parents=True, exist_ok=True)

    def _autofill_settings(self, psse_files, profile_store_file, profile_mapping_file):
        "The method auto populates fields for a new PyPSSE project"

        self._update_setting("sav", "case_study", psse_files)
        self._update_setting("raw", "raw_file", psse_files)
        self._update_setting("snp", "snp_file", psse_files)
        self._update_setting("dyr", "dyr_file", psse_files)
        self._update_setting("gic", "gic_file", psse_files)
        self._update_setting("rwm", "rwm_file", psse_files)

        if "dll" in psse_files:
            self.project.simulation_settings.simulation.user_models = psse_files["dll"]
            logging.info(f"user_models={psse_files['dll']}")
        else:
            logging.info("No DLL files found in project path")

        if "idv" in psse_files:
            self.project.simulation_settings.simulation.setup_files = psse_files["idv"]
            logging.info(
                f"setup_files={psse_files['idv']}"
                f"\nSequence of IDV setup files is important. Manually change in TOML file if needed"
            )
        else:
            logging.info("No IDV files found in project path")

        store_path = self.project_path / PROFILES_FOLDER
        if profile_store_file and Path(profile_store_file).exists():
            assert Path(profile_store_file).suffix.lower() == ".hdf5", "Store file should be a valid hdf5 file"
            copy(profile_store_file, store_path)
        else:
            ProfileManager(None, None, self.project.simulation_settings, logging)

        if profile_mapping_file and Path(profile_mapping_file).exists():
            assert Path(profile_mapping_file).suffix.lower() == ".toml", "Profile mapping should be a valid toml file"
            copy(profile_mapping_file, store_path)
            self.project.simulation_settings.simulation.use_profile_manager = True
        else:
            # TODO: auto generate mapping file from bus subsystem files
            with open(os.path.join(store_path, DEFAULT_PROFILE_MAPPING_FILENAME), "w") as _:
                pass
            self.project.simulation_settings.simulation.use_profile_manager = False

        self._create_default_sub_file()

    def _create_default_sub_file(self):
        "Method creates a subscription file for the HELICS interface"
        subscription_fields = [x.value for x in SubscriptionFileRequiredColumns]
        data = pd.DataFrame({}, columns=list(subscription_fields))
        data.to_csv(self.project_path / DEFAULT_SUBSCRIPTION_FILENAME, index=False)
        logging.info("Creating subscription template")
        self.project.simulation_settings.simulation.subscriptions_file = DEFAULT_SUBSCRIPTION_FILENAME

    def _update_setting(self, f_type, key, psse_files):
        if f_type in psse_files:
            relevent_files = psse_files[f_type]
            setattr(self.project.simulation_settings.simulation, key, relevent_files[0])
            logging.info(f"Settings:{key}={relevent_files[0]}")
            if len(relevent_files) > 1:
                logging.warning(
                    f"More than one file with extension {f_type} exist."
                    f"\nFiles found: {relevent_files}"
                    f"\nManually update the settings toml file"
                )
        else:
            logging.warning(f"No file with extension '{f_type}'")
