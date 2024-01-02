import json
import os
from distutils.dir_util import copy_tree
from pathlib import Path
from shutil import copy

import pandas as pd
import toml
from loguru import logger

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
        self.basepath = Path(__file__).parent

    def create(
        self,
        parent_path: Path,
        project_name: str,
        psse_folder: Path,
        simulation_settings_file: Path,
        export_settings_file: Path,
        profile_store_file: Path,
        profile_mapping_file: Path,
        overwrite: bool = True,
        autofill: bool = True,
    ):
        """The methods creates a new PyPSSE project

        Args:
            parent_path (Path): path to new pypsse project
            project_name (str): project name
            psse_folder (Path): _description_
            simulation_settings_file (Path): simulation settings toml file path
            export_settings_file (Path): export settings toml file path
            profile_store_file (Path): path to a valid Profiles.hdf5 file (Contains profiles for time series simulations)
            profile_mapping_file (Path): path to a valid Profile_mapping.toml file (used to map profile to PSSE elements)
            overwrite (bool, optional): Attempt to auto fill settings. (Verify manually settings file is correct). Defaults to True.
            autofill (bool, optional): Overwrite project is it already exists. Defaults to True.
        """

        self.project_path = Path(parent_path) / project_name

        exports_dict = toml.load(self.basepath / DEFAULTS_FOLDER / EXPORTS_SETTINGS_FILENAME)
        export_settings = ExportFileOptions(**exports_dict)

        if export_settings_file:
            export_settings_file = Path(export_settings_file)
            assert export_settings_file.exists(), f"Export file '{export_settings_file}' does not exist"
            new_export_settings = toml.load(export_settings_file)
            export_settings.update(**new_export_settings)

        sim_setting_dict = toml.load(self.basepath / DEFAULTS_FOLDER / SIMULATION_SETTINGS_FILENAME)
        sim_setting_dict["simulation"]["project_path"] = str(self.project_path)
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

        self._create_folders()

        if psse_folder:
            psse_files = self._copy_psse_project_files(psse_folder)
            if autofill and psse_files:
                self._autofill_settings(psse_files, profile_store_file, profile_mapping_file)

        self._update_export_files()
        self._write_setting_files()

    def _update_export_files(self):
        """sets up export file paths"""
        self.project.simulation_settings.export.out_file = DEFAULT_OUT_FILE
        self.project.simulation_settings.export.outx_file = DEFAULT_OUTX_FILE
        self.project.simulation_settings.export.log_file = DEFAULT_LOG_FILE
        self.project.simulation_settings.export.excel_file = DEFAULT_EXCEL_FILE
        self.project.simulation_settings.export.coordinate_file = DEFAULT_COORDINATES_FILE
        self.project.simulation_settings.export.networkx_graph_file = DEFAULT_GRAPH_FILE

    def _psse_project_file_dict(self, path: Path) -> dict:
        """Creates a mapping of all project files in a folder

        Args:
            path (Path): path (folder) to existing psse project

        Returns:
            dict: mapping of file types to paths
        """

        file_dict = {}
        for _, _, files in os.walk(path):
            for file in files:
                _, ext = file.split(".")
                if ext not in file_dict:
                    file_dict[ext.lower()] = [file]
                else:
                    file_dict[ext.lower()].append(file)
        return file_dict

    def _copy_psse_project_files(self, psse_folder: Path) -> dict:
        """Copies psse files to a new project

        Args:
            psse_folder (Path): path (folder) to existing psse project

        Raises:
            FileExistsError: raised if provided project path does not exist

        Returns:
            dict: mapping of file types to paths
        """

        psse_folder = Path(psse_folder)
        if psse_folder.exists():
            new_path = self.project_path / CASESTUDY_FOLDER
            copy_tree(str(psse_folder.absolute()), str(new_path.absolute()))
            psse_files = self._psse_project_file_dict(new_path)
        else:
            msg = f"PSSE project path does not exist. ({psse_folder}) {os.getcwd()}"
            raise FileExistsError(msg)
        return psse_files

    def _write_setting_files(self):
        """serialized simulation and export setting  files for the new project"""
        sim_file_path = self.project_path / SIMULATION_SETTINGS_FILENAME
        with open(sim_file_path, "w") as f:
            toml.dump(json.loads(self.project.simulation_settings.model_dump_json()), f)
            logger.info(f"writing file : {sim_file_path!s}")

        export_file_path = self.project_path / EXPORTS_SETTINGS_FILENAME
        with open(export_file_path, "w") as f:
            toml.dump(json.loads(self.project.export_settings.model_dump_json()), f)
            logger.info(f"writing file : {export_file_path!s}")

    def _create_folders(self):
        """Creates folder structure for a new project. Older project can be over-written

        Raises:
            FileExistsError: raised if provided folder path does not exist
        """

        for folder in self.project.project_folders:
            project_folder = self.project_path / folder.value
            if project_folder.exists() and not self.project.overwrite:
                msg = "Project folder already exists. Set overwrite=true to overwrite existing projects"
                raise FileExistsError(msg)
            elif not project_folder.exists():
                project_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"folder created: {project_folder!s}")

    def _autofill_settings(self, psse_files: dict, profile_store_file: Path, profile_mapping_file: Path):
        """The method auto populates fields for a new PyPSSE project

        Args:
            psse_files (dict): mapping of file type to file path
            profile_store_file (Path): path to profile store file (hdf5)
            profile_mapping_file (Path): path to profile mapping file (toml)
        """

        self._update_setting("sav", "case_study", psse_files)
        self._update_setting("raw", "raw_file", psse_files)
        self._update_setting("snp", "snp_file", psse_files)
        self._update_setting("dyr", "dyr_file", psse_files)
        self._update_setting("gic", "gic_file", psse_files)
        self._update_setting("rwm", "rwm_file", psse_files)

        if "dll" in psse_files:
            self.project.simulation_settings.simulation.user_models = psse_files["dll"]
            logger.info(f"user_models={psse_files['dll']}")
        else:
            logger.info("No DLL files found in project path")

        if "idv" in psse_files:
            self.project.simulation_settings.simulation.setup_files = psse_files["idv"]
            logger.info(
                f"setup_files={psse_files['idv']}"
                f"\nSequence of IDV setup files is important. Manually change in TOML file if needed"
            )
        else:
            logger.info("No IDV files found in project path")

        store_path = self.project_path / PROFILES_FOLDER
        if profile_store_file and Path(profile_store_file).exists():
            assert Path(profile_store_file).suffix.lower() == ".hdf5", "Store file should be a valid hdf5 file"
            copy(profile_store_file, store_path)
        else:
            ProfileManager(None, self.project.simulation_settings)

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
        """Method creates a subscription file for the HELICS interface"""

        subscription_fields = [x.value for x in SubscriptionFileRequiredColumns]
        data = pd.DataFrame({}, columns=list(subscription_fields))
        data.to_csv(self.project_path / DEFAULT_SUBSCRIPTION_FILENAME, index=False)
        logger.info("Creating subscription template")
        self.project.simulation_settings.simulation.subscriptions_file = DEFAULT_SUBSCRIPTION_FILENAME

    def _update_setting(self, f_type: str, key: str, psse_files: dict):
        """updates settings for the new project

        Args:
            f_type (str): file type
            key (str): simulation setting to update
            psse_files (dict): mapping of file type to file path
        """
        if f_type in psse_files:
            relevent_files = psse_files[f_type]
            setattr(self.project.simulation_settings.simulation, key, relevent_files[0])
            logger.info(f"Settings:{key}={relevent_files[0]}")
            if len(relevent_files) > 1:
                logger.warning(
                    f"More than one file with extension {f_type} exist."
                    f"\nFiles found: {relevent_files}"
                    f"\nManually update the settings toml file"
                )
        else:
            logger.warning(f"No file with extension '{f_type}'")
