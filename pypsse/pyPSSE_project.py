from pypsse.ProfileManager.ProfileStore import ProfileManager
from distutils.dir_util import copy_tree
from shutil import copy
from pypsse.common import *
import pandas as pd
import logging
import pypsse
import shutil
import toml
import os


class pypsse_project:

    def __init__(self):
        logging.root.setLevel("DEBUG")
        self.basepath = os.path.dirname(getattr(pypsse, "__path__")[0])
        pass

    def create(self, path, projectName, PSSEfolder, settings, exportSettings, ProfileStore, profile_mapping,
               overwrite=True, autofill=True):
        if os.path.exists(path):
            self._create_folders(path, projectName, overwrite)
            uSettings, uExports = self._update_settings(settings, exportSettings)
            uSettings["Simulation"]["Project Path"] = os.path.join(path, projectName)

            psseFiles = self._copy_psse_project_files(path, projectName, PSSEfolder)
            if autofill:
                uSettings = self._autofill_settings(
                    psseFiles, uSettings, path, projectName, ProfileStore, profile_mapping
                )
            self._write_setting_files(path, projectName, uSettings, uExports)

        else:
            raise Exception(f"Path provided does not exist ({path})")

    def _autofill_settings(self, psseFiles, uSettings, path, projectName, ProfileStore, profile_mapping):
        pssePath = os.path.join(path, projectName, "Case_study")

        uSettings = self._set_file("sav", "Case study", psseFiles, uSettings, pssePath)
        uSettings = self._set_file("raw", "Raw file", psseFiles, uSettings, pssePath)
        uSettings = self._set_file("snp", "Snp file", psseFiles, uSettings, pssePath)
        uSettings = self._set_file("dyr", "Dyr file", psseFiles, uSettings, pssePath)
        uSettings = self._set_file("gic", "GIC file", psseFiles, uSettings, pssePath)
        uSettings = self._set_file("rwm", "Rwm file", psseFiles, uSettings, pssePath)
        if "dll" in psseFiles:
            uSettings["Simulation"]["User models"] = psseFiles["dll"]
            logging.info(f"Settings:User models={psseFiles['dll']}")
        else:
            logging.info(f"No DLL files found in path {pssePath}")
        if "idv" in psseFiles:
            uSettings["Simulation"]["Setup files"] = psseFiles["idv"]
            logging.info(f"Settings:Setup files={psseFiles['idv']}"
                         f"\nSequence of IDV setup files is important. Manually change in TOML file f needed")
        else:
            logging.info(f"No IDV files found in path {pssePath}")

        if "csv" in psseFiles:
            subscriptonFile = self._find_subscriptions_file(psseFiles["csv"], uSettings, pssePath)
            if subscriptonFile:
                uSettings["Simulation"]["Subscriptions file"] = subscriptonFile
                logging.info(f"Settings:Subscriptions file={subscriptonFile}")
            else:
                uSettings = self._create_default_sub_file(pssePath, uSettings)
        else:
            uSettings = self._create_default_sub_file(pssePath, uSettings)

        storePath = os.path.join(path, projectName, "Profiles")
        if ProfileStore and os.path.exists(ProfileStore):
            try:
                copy(ProfileStore, storePath)
            except:
                raise Exception(os.getcwd(),ProfileStore, storePath)
        else:
            ProfileManager(None, None, uSettings, logging)

        if os.path.exists(profile_mapping):
            copy(profile_mapping, storePath)
        else:
            #TODO: auto generate mapping file from bus subsystem files
            with open(os.path.join(storePath, DEFAULT_PROFILE_MAPPING_FILENAME), "w") as f:
                pass

        return uSettings

    def _create_default_sub_file(self, pssePath, uSettings):
        data = pd.DataFrame({}, columns=list(SUBSCRIPTION_FIELDS))
        data.to_csv(os.path.join(pssePath, DEFAULT_SUBSCRIPTION_FILENAMES), index=False)
        logging.info(f"No valid HELICS subscriptions file found in path {pssePath}."
                     f"Creating empty {DEFAULT_SUBSCRIPTION_FILENAMES} file")
        uSettings["Simulation"]["Subscriptions file"] = DEFAULT_SUBSCRIPTION_FILENAMES
        return uSettings

    def _find_subscriptions_file(self, fileList, uSettings, pssePath):
        sFile = None
        for fi in fileList:
            fPath = os.path.join(pssePath, fi)
            with open(fPath, 'r') as f:
                line = f.readline()
            lData = set(line.split(","))
            if SUBSCRIPTION_FIELDS.issubset(lData):
                sFile = fi
                break
        return sFile

    def _set_file(self, fType, key, psseFiles, settingsDict, pssePath):
        if fType in psseFiles:
            releventFiles = psseFiles[fType]
            settingsDict["Simulation"][key] =releventFiles[0]
            logging.info(f"Settings:{key}={releventFiles[0]}")
            if len(releventFiles) > 1:
                logging.warning(f"More than one file with extension {fType} exist."
                                f"\nFiles found: {releventFiles}"
                                f"\nManually update the settings toml file")
        else:
            logging.warning(f"No file with extension '{fType}' in path {pssePath}")
        return settingsDict

    def _psse_project_file_dict(self, path):
        fileDict = {}
        for root, dirs, files in os.walk(path):
            for file in files:
                fName, ext = file.split(".")
                if ext not in fileDict:
                    fileDict[ext.lower()] = [file]
                else:
                    fileDict[ext.lower()].append(file)
        return fileDict

    def _copy_psse_project_files(self, path, projectName, PSSEfolder):
        if os.path.exists(PSSEfolder):
            newPath = os.path.join(path, projectName, "Case_study")
            copy_tree(PSSEfolder, os.path.join(path, newPath))
            psseFiles = self._psse_project_file_dict(newPath)
        else:
            #print(os.getcwd())
            raise Exception(f"PSSE project path does not exist. ({PSSEfolder}) {os.getcwd()}")
        return psseFiles

    def _update_settings(self, settings, exportSettings):
        defaultSettings = toml.load(os.path.join(self.basepath, "pypsse", 'defaults', SIMULATION_SETTINGS_FILENAME))
        defaultExports = toml.load(os.path.join(self.basepath, "pypsse", 'defaults', EXPORTS_SETTINGS_FILENAME))
        defaultSettings.update(settings)
        defaultExports.update(exportSettings)
        return defaultSettings, defaultExports

    def _write_setting_files(self, path, projectName, settings, exports):
        with open(os.path.join(path, projectName, 'Settings', SIMULATION_SETTINGS_FILENAME), 'w') as f:
            toml.dump(settings, f)

        with open(os.path.join(path, projectName, 'Settings', EXPORTS_SETTINGS_FILENAME), 'w') as f:
            toml.dump(exports, f)
        return

    def _create_folders(self, path, projectName, overwrite):
        projectPath = os.path.join(path, projectName)
        if os.path.exists(projectPath) and overwrite:
            os.system('rmdir /S /Q "{}"'.format(projectPath))
            #os.remove(projectPath)
        elif os.path.exists(projectPath) and not overwrite:
            raise Exception(f"Project already exists. Set 'overwrite' to true to overwrite existing project.")

        self.makeDIR(projectPath)
        for f in PROJECT_FOLDERS:
            self.makeDIR(os.path.join(projectPath, f))

    def makeDIR(self, path):
        #try:
            os.mkdir(path)
       # except OSError:
       #     raise Exception(f"Creation of the directory {path} failed; {OSError}")

# a = pyPSSE_project()
# a.create(
#     r"C:\Users\alatif\Desktop\pypsse-usecases",
#     "TestProject",
#     r"C:\Users\alatif\Desktop\pypsse-usecases\PSSE_WECC_model\Case_study",
#     {},
#     {},
# )