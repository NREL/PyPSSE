from pypsse.ProfileManager.common import PROFILE_VALIDATION
import numpy as np
import datetime
import copy

class Profile:

    DEFAULT_SETTINGS = {
        "multiplier": 1,
        "normalize": False,
        "interpolate": False
    }

    def __init__(self, profileObj, Solver, mappingDict,  bufferSize=10, neglectYear=True):
        self.valueSettings = {f"{x['bus']}__{x['id']}": {**self.DEFAULT_SETTINGS, **x} for x in mappingDict}
        self.mappingDict = mappingDict
        self.bufferSize = bufferSize
        self.buffer = np.zeros(bufferSize)
        self.profile = profileObj
        self.neglectYear = neglectYear
        self.Solver = Solver
        self.attrs = self.profile.attrs
        S = self.attrs["sTime"].decode()
        stime = S if "." in S else S + ".00"
        E = self.attrs["eTime"].decode()
        etime = E if "." in E else E + ".00"
        self.sTime = datetime.datetime.strptime(stime, '%Y-%m-%d %H:%M:%S.%f')
        self.eTime = datetime.datetime.strptime(etime, '%Y-%m-%d %H:%M:%S.%f')
        self.simRes = self.Solver.GetStepSizeSec()
        self.Time = copy.deepcopy(self.Solver.getTime())
        self.Columns = self.attrs["units"]
        self.dType = self.attrs["type"].decode()
        return

    def update(self, updateObjectProperties=True):
        self.Time = copy.deepcopy(self.Solver.getTime())
        if self.Time < self.sTime or self.Time > self.eTime:
            value = np.array([0] * len(self.profile[0]))
            value1 = np.array([0] * len(self.profile[0]))
        else:
            dT = (self.Time - self.sTime).total_seconds()
            n = int(dT / self.attrs["resTime"])
            value = np.array(list(self.profile[n]))

            dT2 = (self.Time - (self.sTime + datetime.timedelta(seconds=int(n * self.attrs["resTime"])))).total_seconds()
            value1 = np.array(list(self.profile[n])) + (
                    np.array(list(self.profile[n+1])) - np.array(list(self.profile[n]))
            ) * dT2 / self.attrs["resTime"]

        if updateObjectProperties:
            for objName in self.valueSettings:
                bus, id = objName.split("__")
                if self.valueSettings[objName]['interpolate']:
                    value = value1
                mult = self.valueSettings[objName]['multiplier']
                if self.valueSettings[objName]['normalize']:
                    valueF = value / self.attrs["max"] * mult
                else:
                    valueF = value * mult
                valueF = self.fill_missing_values(valueF)
                self.Solver.update_object(self.dType, bus, id, valueF)
        return value

    def fill_missing_values(self, value):
        idx = [f'realar{PROFILE_VALIDATION[self.dType].index(c) + 1}' for c in self.Columns]
        x = dict(zip(idx, list(value)))
        return x
