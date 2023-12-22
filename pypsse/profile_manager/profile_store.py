import datetime

import h5py
import numpy as np
import pandas as pd
import toml

from pypsse.common import DEFAULT_PROFILE_MAPPING_FILENAME, DEFAULT_PROFILE_STORE_FILENAME, PROFILES_FOLDER
from pypsse.exceptions import InvalidParameterError
from pypsse.models import SimulationSettings
from pypsse.profile_manager.common import PROFILE_VALIDATION, ProfileTypes
from pypsse.profile_manager.profile import Profile


class ProfileManager:
    """Implentation for the profile manager for PyPSSE.
    Enables attacheing profilse to all PSSE objects and associated properties"""

    def __init__(self, pypsse_objects, solver, settings: SimulationSettings, logger, mode="r+"):
        self._logger = logger
        self.solver = solver
        self.objects = pypsse_objects
        self.settings = settings

        file_path = settings.simulation.project_path / PROFILES_FOLDER / DEFAULT_PROFILE_STORE_FILENAME

        if file_path.exists():
            self._logger.info("Loading existing h5 store")
            self.store = h5py.File(file_path, mode)
        else:
            self._logger.info("Creating new h5 store")
            self.store = h5py.File(file_path, "w")
            for profile_group in ProfileTypes.names():
                self.store.create_group(profile_group)

    def load_data(self, file_path):
        "Load in external profile data"
        toml_dict = toml.load(file_path)
        return toml_dict

    def setup_profiles(self):
        "Sets up all profiles in the profile manager"
        mapping_path = self.settings.simulation.project_path / PROFILES_FOLDER / DEFAULT_PROFILE_MAPPING_FILENAME
        if mapping_path.exists():
            self.profile_mapping = self.load_data(mapping_path)
            self.profiles = {}
            for group, profile_map in self.profile_mapping.items():
                if group in self.store:
                    grp = self.store[group]
                    for profile_name, mapping_dict in profile_map.items():
                        if profile_name in grp:
                            self.profiles[f"{group}/{profile_name}"] = Profile(
                                grp[profile_name], self.solver, mapping_dict
                            )
                        else:
                            self._logger.warning(rf"Group {group} \ data set {profile_name} not found in the h5 store")
                else:
                    self._logger.warning(f"Group {group} not found in the h5 store")
        else:
            msg = f"Profile_mapping.toml file does not exist in path {mapping_path}"
            raise Exception(msg)

    def create_dataset(self, dname, p_type, data, start_time, resolution, _, info):
        "Craete datasets for a PyPSSE project"
        grp = self.store[p_type]
        if dname not in grp:
            sa, sa_type = self.df_to_sarray(data)
            dset = grp.create_dataset(
                dname, data=sa, chunks=True, compression="gzip", compression_opts=4, shuffle=True, dtype=sa_type
            )
            self.create_metadata(dset, start_time, resolution, data, list(data.columns), info, p_type)
        else:
            self._logger.error(f'Data set "{dname}" already exists in group "{p_type}".')
            msg = f'Data set "{dname}" already exists in group "{p_type}".'
            raise Exception(msg)

    def df_to_sarray(self, df):
        "Enables data converson"

        def make_col_type(col_type, col):
            try:
                if "numpy.object_" in str(col_type.type):
                    maxlens = col.dropna().str.len()
                    if maxlens.any():
                        maxlen = maxlens.max().astype(int)
                        col_type = ("S%s" % maxlen, 1)
                    else:
                        col_type = "f2"
                return col.name, col_type
            except:
                raise

        v = df.values
        types = df.dtypes
        numpy_struct_types = [make_col_type(types[col], df.loc[:, col]) for col in df.columns]
        dtype = np.dtype(numpy_struct_types)
        z = np.zeros(v.shape[0], dtype)
        for i, k in enumerate(z.dtype.names):
            # This is in case you have problems with the encoding, remove the if branch if not
            try:
                if dtype[i].str.startswith("|S"):
                    z[k] = df[k].str.encode("latin").astype("S")
                else:
                    z[k] = v[:, i]
            except:
                raise

        return z, dtype

    def add_profiles_from_csv(self, csv_file, name, p_type, start_time, resolution_sec=900, units="", info=""):
        "Enables profiles from existing csv files"
        if p_type not in PROFILE_VALIDATION:
            msg = f"Valid profile types are: {list(PROFILE_VALIDATION.keys())}"
            raise Exception(msg)
        data = pd.read_csv(csv_file)
        for c in data.columns:
            if c not in PROFILE_VALIDATION[p_type]:
                msg = f"{c} is not valid, Valid subtypes for '{p_type}' are: {PROFILE_VALIDATION[p_type]}"
                raise Exception(msg)
        self.add_profiles(name, p_type, data, start_time, resolution_sec=resolution_sec, units=units, info=info)

    def add_profiles(self, name, p_type, data, start_time, resolution_sec=900, units="", info=""):
        "Adds a profile to the profile manager"
        if type(start_time) is not datetime.datetime:
            msg = "start_time should be a python datetime object"
            raise InvalidParameterError(msg)
        if p_type not in ProfileTypes.names():
            msg = f"Valid values for p_type are {ProfileTypes.names()}"
            raise InvalidParameterError(msg)
        self.create_dataset(name, p_type, data, start_time, resolution_sec, units=units, info=info)

    def create_metadata(self, d_set, start_time, resolution, data, units, info, p_type):
        "Adds a metadata to a profile"
        metadata = {
            "sTime": str(start_time),
            "eTime": str(start_time + datetime.timedelta(seconds=resolution * len(data))),
            "resTime": resolution,
            "npts": len(data),
            "min": data.min(),
            "max": data.max(),
            "mean": np.mean(data),
            "units": units,
            "info": info,
            "type": p_type,
        }
        for key, value in metadata.items():
            if isinstance(value, str):
                value_mod = np.string_(value)
            else:
                value_mod = value
            d_set.attrs[key] = value_mod

    def update(self):
        "Returns data for the current timestep for all mapped profiles"
        results = {}
        for profile_name, profile_obj in self.profiles.items():
            result = profile_obj.update()
            results[profile_name] = result
        return results

    def __del__(self):
        self.store.flush()
