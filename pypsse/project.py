import logging
import os
from distutils.dir_util import copy_tree
from shutil import copy, rmtree

import pandas as pd
import toml

import pypsse
from pypsse.common import (
    DEFAULT_PROFILE_MAPPING_FILENAME,
    DEFAULT_SUBSCRIPTION_FILENAMES,
    EXPORTS_SETTINGS_FILENAME,
    PROJECT_FOLDERS,
    SIMULATION_SETTINGS_FILENAME,
    SUBSCRIPTION_FIELDS,
)
from pypsse.profile_manager.profile_store import ProfileManager


class Project:
    "This class defines the structure of a PyPSSE project"

    def __init__(self):
        logging.root.setLevel("DEBUG")
        self.basepath = os.path.dirname(pypsse.__path__[0])
        pass

    def create(
        self,
        path,
        project_name,
        psse_folder,
        settings,
        export_settings,
        profile_store,
        profile_mapping,
        overwrite=True,
        autofill=True,
    ):
        "The methods creates a new PyPSSE project"
        if os.path.exists(path):
            self._create_folders(path, project_name, overwrite)
            u_settings, u_exports = self._update_settings(settings, export_settings)
            u_settings["Simulation"]["Project Path"] = os.path.join(path, project_name)

            psse_files = self._copy_psse_project_files(path, project_name, psse_folder)
            if autofill:
                u_settings = self._autofill_settings(
                    psse_files, u_settings, path, project_name, profile_store, profile_mapping
                )
            self._write_setting_files(path, project_name, u_settings, u_exports)

        else:
            msg = f"Path provided does not exist ({path})"
            raise Exception(msg)

    def _autofill_settings(self, psse_files, u_settings, path, project_name, profile_store, profile_mapping):
        "The method auto populates fields for a new PyPSSE project"
        psse_path = os.path.join(path, project_name, "Case_study")

        u_settings = self._set_file("sav", "Case study", psse_files, u_settings, psse_path)
        u_settings = self._set_file("raw", "Raw file", psse_files, u_settings, psse_path)
        u_settings = self._set_file("snp", "Snp file", psse_files, u_settings, psse_path)
        u_settings = self._set_file("dyr", "Dyr file", psse_files, u_settings, psse_path)
        u_settings = self._set_file("gic", "GIC file", psse_files, u_settings, psse_path)
        u_settings = self._set_file("rwm", "Rwm file", psse_files, u_settings, psse_path)
        if "dll" in psse_files:
            u_settings["Simulation"]["User models"] = psse_files["dll"]
            logging.info(f"Settings:User models={psse_files['dll']}")
        else:
            logging.info(f"No DLL files found in path {psse_path}")
        if "idv" in psse_files:
            u_settings["Simulation"]["Setup files"] = psse_files["idv"]
            logging.info(
                f"Settings:Setup files={psse_files['idv']}"
                f"\nSequence of IDV setup files is important. Manually change in TOML file f needed"
            )
        else:
            logging.info(f"No IDV files found in path {psse_path}")

        if "csv" in psse_files:
            subscripton_file = self._find_subscriptions_file(psse_files["csv"], psse_path)
            if subscripton_file:
                u_settings["Simulation"]["Subscriptions file"] = subscripton_file
                logging.info(f"Settings:Subscriptions file={subscripton_file}")
            else:
                u_settings = self._create_default_sub_file(psse_path, u_settings)
        else:
            u_settings = self._create_default_sub_file(psse_path, u_settings)

        store_path = os.path.join(path, project_name, "Profiles")
        if profile_store and os.path.exists(profile_store):
            copy(profile_store, store_path)
        else:
            ProfileManager(None, None, u_settings, logging)

        if os.path.exists(profile_mapping):
            copy(profile_mapping, store_path)
        else:
            # TODO: auto generate mapping file from bus subsystem files
            with open(os.path.join(store_path, DEFAULT_PROFILE_MAPPING_FILENAME), "w") as _:
                pass

        return u_settings

    def _create_default_sub_file(self, psse_path, u_settings):
        "Method creates a subscription file for the HELICS interface"
        data = pd.DataFrame({}, columns=list(SUBSCRIPTION_FIELDS))
        data.to_csv(os.path.join(psse_path, DEFAULT_SUBSCRIPTION_FILENAMES), index=False)
        logging.info(
            f"No valid HELICS subscriptions file found in path {psse_path}."
            f"Creating empty {DEFAULT_SUBSCRIPTION_FILENAMES} file"
        )
        u_settings["Simulation"]["Subscriptions file"] = DEFAULT_SUBSCRIPTION_FILENAMES
        return u_settings

    def _find_subscriptions_file(self, file_list, psse_path):
        "Validates an existing subscription file for the HELICS interface"
        s_file = None
        for fi in file_list:
            f_path = os.path.join(psse_path, fi)
            with open(f_path) as f:
                line = f.readline()
            l_data = set(line.split(","))
            if SUBSCRIPTION_FIELDS.issubset(l_data):
                s_file = fi
                break
        return s_file

    def _set_file(self, f_type, key, psse_files, settings_dict, psse_path):
        if f_type in psse_files:
            relevent_files = psse_files[f_type]
            settings_dict["Simulation"][key] = relevent_files[0]
            logging.info(f"Settings:{key}={relevent_files[0]}")
            if len(relevent_files) > 1:
                logging.warning(
                    f"More than one file with extension {f_type} exist."
                    f"\nFiles found: {relevent_files}"
                    f"\nManually update the settings toml file"
                )
        else:
            logging.warning(f"No file with extension '{f_type}' in path {psse_path}")
        return settings_dict

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

    def _copy_psse_project_files(self, path, project_name, psse_folder):
        "Copies PSSE file to the new project folder"
        if os.path.exists(psse_folder):
            new_path = os.path.join(path, project_name, "Case_study")
            copy_tree(psse_folder, os.path.join(path, new_path))
            psse_files = self._psse_project_file_dict(new_path)
        else:
            msg = f"PSSE project path does not exist. ({psse_folder}) {os.getcwd()}"
            raise Exception(msg)
        return psse_files

    def _update_settings(self, settings, export_settings):
        "Unables update of an existing settings file"
        default_settings = toml.load(os.path.join(self.basepath, "pypsse", "defaults", SIMULATION_SETTINGS_FILENAME))
        default_exports = toml.load(os.path.join(self.basepath, "pypsse", "defaults", EXPORTS_SETTINGS_FILENAME))
        default_settings.update(settings)
        default_exports.update(export_settings)
        return default_settings, default_exports

    def _write_setting_files(self, path, project_name, settings, exports):
        "Creats a new settings file"
        with open(os.path.join(path, project_name, "Settings", SIMULATION_SETTINGS_FILENAME), "w") as f:
            toml.dump(settings, f)

        with open(os.path.join(path, project_name, "Settings", EXPORTS_SETTINGS_FILENAME), "w") as f:
            toml.dump(exports, f)

    def _create_folders(self, path, project_name, overwrite):
        "Creates folder structure for a new project. Older project can be over-written"
        project_path = os.path.join(path, project_name)
        if os.path.exists(project_path) and overwrite:
            rmtree(project_path)
        elif os.path.exists(project_path) and not overwrite:
            msg = "Project already exists. Set 'overwrite' to true to overwrite existing project."
            raise Exception(msg)

        self.make_dir(project_path)
        for f in PROJECT_FOLDERS:
            self.make_dir(os.path.join(project_path, f))

    def make_dir(self, path):
        # try:
        os.mkdir(path)
