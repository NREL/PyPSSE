from PyDSS.ProfileManager.Profile import Profile as TSP
from PyDSS.ProfileManager.common import PROFILE_TYPES
from PyDSS.exceptions import InvalidParameter
from PyDSS.pyLogger import getLoggerTag
from PyDSS.utils.utils import load_data
from datetime import datetime
import pandas as pd
import numpy as np
import datetime
import logging
import toml
import h5py
import os



class ProfileManager:

    def __init__(self,  dssObjects, dssSolver, options, mode="r+"):
        if options["Logging"]["Pre-configured logging"]:
            logger_tag = __name__
        else:
            logger_tag = getLoggerTag(options)
        self._logger = logging.getLogger(logger_tag)
        self.dssSolver = dssSolver
        self.Objects = dssObjects

        self.profileMapping = load_data(options['Profiles']["Profile mapping"])

        filePath = options['Profiles']["Profile store path"]
        if os.path.exists(filePath):
            self._logger.info("Loading existing h5 store")
            self.store = h5py.File(filePath, mode)
        else:
            self._logger.info("Creating new h5 store")
            self.store = h5py.File(filePath, "w")
            for profileGroup in PROFILE_TYPES.names():
                self.store.create_group(profileGroup)
        return

    def setup_profiles(self):
        self.Profiles = {}
        for group, profileMap in self.profileMapping.items():
            if group in self.store:
                grp = self.store[group]
                for profileName, mappingDict in profileMap.items():
                    if profileName in grp:
                        objects = {x['object'] : self.Objects[x['object']] for x in mappingDict}
                        self.Profiles[f"{group}/{profileName}"] = TSP(grp[profileName], objects, self.dssSolver,
                                                                      mappingDict)
                    else:
                        self._logger.warning("Group {} \ data set {} not found in the h5 store".format(
                            group, profileName
                        ))
            else:
                self._logger.warning("Group {} not found in the h5 store".format(group))
        return

    def create_dataset(self, dname, pType, data ,startTime, resolution, units, info):
        grp = self.store[pType]
        if dname not in grp:
            dset = grp.create_dataset(
                dname,
                data=data,
                shape=(len(data),),
                maxshape=(None,),
                chunks=True,
                compression="gzip",
                compression_opts=4,
                shuffle=True
            )
            self.createMetadata(
                dset, startTime, resolution, data, units, info
            )
        else:
            self._logger.error('Dataset "{}" already exists in group "{}".'.format(dname, pType))
            raise Exception('Dataset "{}" already exists in group "{}".'.format(dname, pType))

    def add_from_arrays(self, data, name, pType, startTime, resolution, units="", info=""):
        data = np.array(data)
        r, c = data.shape
        if r > c:
            for i in range(c):
                d = data[:, i]
                dname = name if i==0 else "{}_{}".format(name, i)
                self.create_dataset(dname=dname, pType=pType, data=d, startTime=startTime, resolution=resolution,
                                    units=units, info=info)
        else:
            for i in range(r):
                d = data[i, :]
                dname = name if i==0 else "{}_{}".format(name, i)
                self.create_dataset(dname=dname, pType=pType, data=d, startTime=startTime, resolution=resolution,
                                    units=units, info=info)
        return

    def add_profiles_from_csv(self, csv_file, name, pType, startTime, resolution_sec=900, units="",
                              info=""):
        data = pd.read_csv(csv_file).values
        self.add_profiles(data, name, pType, startTime, resolution_sec=resolution_sec, units=units, info=info)


    def add_profiles(self, data, name, pType, startTime, resolution_sec=900, units="", info=""):
        if type(startTime) is not datetime.datetime:
            raise InvalidParameter("startTime should be a python datetime object")
        if pType not in PROFILE_TYPES.names():
            raise InvalidParameter("Valid values for pType are {}".format(PROFILE_TYPES.names()))
        if data:
            self.add_from_arrays(data, name, pType, startTime, resolution_sec, units=units, info=info)
        return

    def createMetadata(self, dSet, startTime, resolution, data, units, info):
        metadata = {
            "sTime": str(startTime),
            "eTime": str(startTime + datetime.timedelta(seconds=resolution*len(data))),
            "resTime": resolution,
            "npts": len(data),
            "min": min(data),
            "max": max(data),
            "mean": np.mean(data),
            "units": units,
            "info": info,
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
