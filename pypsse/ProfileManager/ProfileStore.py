from pypsse.ProfileManager.common import PROFILE_TYPES, PROFILE_VALIDATION
from pypsse.ProfileManager.Profile import Profile as TSP
from pypsse.exceptions import InvalidParameter
from datetime import datetime as dt
from pypsse.common import *
import pandas as pd
import numpy as np
import datetime
import toml
import h5py
import os

class ProfileManager:

    def __init__(self,  pypsseObjects, Solver, settings, logger, mode="r+"):
        self._logger = logger
        self.Solver = Solver
        self.Objects = pypsseObjects
        self.settings = settings
        filePath = os.path.join(settings["Simulation"]["Project Path"], "Profiles", "Profiles.hdf5")

        if os.path.exists(filePath):
            self._logger.info("Loading existing h5 store")
            self.store = h5py.File(filePath, mode)
        else:
            self._logger.info("Creating new h5 store")
            self.store = h5py.File(filePath, "w")
            for profileGroup in PROFILE_TYPES.names():
                self.store.create_group(profileGroup)
        return

    def load_data(self, filePath):
        if os.path.exists(filePath):
            tomlDict = toml.load(filePath)
        else:
            raise Exception(f'{filePath}: the path does not exist')
        return tomlDict

    def setup_profiles(self):
        mappingPath = os.path.join(self.settings["Simulation"]["Project Path"], "Profiles", "Profile_mapping.toml")
        if os.path.exists(mappingPath):
            self.profileMapping = self.load_data(mappingPath)
            self.Profiles = {}
            for group, profileMap in self.profileMapping.items():
                if group in self.store:
                    grp = self.store[group]
                    for profileName, mappingDict in profileMap.items():
                        if profileName in grp:
                            self.Profiles[f"{group}/{profileName}"] = TSP(grp[profileName], self.Solver, mappingDict)
                        else:
                            self._logger.warning("Group {} \ data set {} not found in the h5 store".format(
                                group, profileName
                            ))
                else:
                    self._logger.warning("Group {} not found in the h5 store".format(group))
        else:
            raise Exception(f"Profile_mapping.toml file does not exist in path {mappingPath}")
        return

    def create_dataset(self, dname, pType, data ,startTime, resolution, units, info):
        grp = self.store[pType]
        if dname not in grp:
            sa, saType = self.df_to_sarray(data)
            dset = grp.create_dataset(
                dname,
                data=sa,
                chunks=True,
                compression="gzip",
                compression_opts=4,
                shuffle=True,
                dtype=saType
            )
            self.createMetadata(
                dset, startTime, resolution, data, list(data.columns), info, pType
            )
        else:
            self._logger.error('Data set "{}" already exists in group "{}".'.format(dname, pType))
            raise Exception('Data set "{}" already exists in group "{}".'.format(dname, pType))

    def df_to_sarray(self, df):

        def make_col_type(col_type, col):
            try:
                if 'numpy.object_' in str(col_type.type):
                    maxlens = col.dropna().str.len()
                    if maxlens.any():
                        maxlen = maxlens.max().astype(int)
                        col_type = ('S%s' % maxlen, 1)
                    else:
                        col_type = 'f2'
                return col.name, col_type
            except:
                raise

        v = df.values
        types = df.dtypes
        numpy_struct_types = [make_col_type(types[col], df.loc[:, col]) for col in df.columns]
        dtype = np.dtype(numpy_struct_types)
        z = np.zeros(v.shape[0], dtype)
        for (i, k) in enumerate(z.dtype.names):
            # This is in case you have problems with the encoding, remove the if branch if not
            try:
                if dtype[i].str.startswith('|S'):
                    z[k] = df[k].str.encode('latin').astype('S')
                else:
                    z[k] = v[:, i]
            except:
                raise

        return z, dtype

    def add_profiles_from_csv(self, csv_file, name, pType, startTime, resolution_sec=900, units="",
                              info=""):
        if pType not in PROFILE_VALIDATION:
            raise Exception(f"Valid profile types are: {list(PROFILE_VALIDATION.keys())}")
        data = pd.read_csv(csv_file)
        for c in data.columns:
            if c not in PROFILE_VALIDATION[pType]:
                raise Exception(f"{c} is not valid, Valid subtypes for '{pType}' are: {PROFILE_VALIDATION[pType]}")
        self.add_profiles(name, pType, data, startTime, resolution_sec=resolution_sec, units=units, info=info)

    def add_profiles(self, name, pType, data, startTime, resolution_sec=900, units="", info=""):
        if type(startTime) is not datetime.datetime:
            raise InvalidParameter("startTime should be a python datetime object")
        if pType not in PROFILE_TYPES.names():
            raise InvalidParameter("Valid values for pType are {}".format(PROFILE_TYPES.names()))
        self.create_dataset(name, pType, data, startTime, resolution_sec, units=units, info=info)
        return

    def createMetadata(self, dSet, startTime, resolution, data, units, info, pType):
        metadata = {
            "sTime": str(startTime),
            "eTime": str(startTime + datetime.timedelta(seconds=resolution*len(data))),
            "resTime": resolution,
            "npts": len(data),
            "min": data.min(),
            "max": data.max(),
            "mean": np.mean(data),
            "units": units,
            "info": info,
            "type": pType
        }
        for key, value in metadata.items():
            if isinstance(value, str):
                value = np.string_(value)
            dSet.attrs[key] = value
        return

    def remove_profile(self, profile_type, profile_name):
        return

    def update(self):
        results = {}
        for profileaName, profileObj in self.Profiles.items():
            result = profileObj.update()
            results[profileaName] = result
        return results

    def __del__(self):
        self.store.flush()

if __name__ == '__main__':
    class Solver:

        def __init__(self):
            self.Time = dt.strptime("09/19/2018 13:55:26", "%m/%d/%Y %H:%M:%S")
            return

        def getTime(self):
            return self.Time

        def GetStepSizeSec(self):
            return 1.0

        def updateTime(self):
            self.Time = self.Time + datetime.timedelta(seconds=1)
            return

        def update_object(self, dType, bus, id, value):
            pass

    settings = toml.load(r"C:\Users\alatif\Desktop\pypsse-usecases\PSSE_WECC_model\Settings\pyPSSE_settings.toml")
    solver = Solver()
    a = ProfileManager(None, solver, settings)
    # a.setup_profiles()
    # for i in range(30):
    #     a.update()
    #     solver.updateTime()

    a.add_profiles_from_csv(
        csv_file=r"C:\Users\alatif\Desktop\pypsse-usecases\PSSE_WECC_model\Profiles\machine.csv",
        name="test",
        pType="Machine",
        startTime=dt.strptime("2018-09-19 13:55:26.001", "%Y-%m-%d %H:%M:%S.%f"),
        resolution_sec=1,
        units="MW",
    )
