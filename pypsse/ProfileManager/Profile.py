import numpy as np
import datetime
import copy

class Profile:

    DEFAULT_SETTINGS = {
        "multiplier": 1,
        "normalize": False,
        "interpolate": False
    }

    def __init__(self, profileObj, objects, dssSolver, mappingDict,  bufferSize=10, neglectYear=True):

        self.valueSettings = {x['object'] : {**self.DEFAULT_SETTINGS, **x} for x in mappingDict}
        self.mappingDict = mappingDict
        self.bufferSize = bufferSize
        self.buffer = np.zeros(bufferSize)
        self.profile = profileObj
        self.neglectYear = neglectYear
        self.Objects = objects
        self.dssSolver = dssSolver
        self.attrs = self.profile.attrs
        self.sTime = datetime.datetime.strptime(self.attrs["sTime"].decode(), '%Y-%m-%d %H:%M:%S.%f')
        self.eTime = datetime.datetime.strptime(self.attrs["eTime"].decode(), '%Y-%m-%d %H:%M:%S.%f')
        self.simRes = self.dssSolver.GetStepSizeSec()
        self.Time = copy.deepcopy(self.dssSolver.GetDateTime())
        return

    def update(self, updateObjectProperties=True):
        self.Time = copy.deepcopy(self.dssSolver.GetDateTime())
        if self.Time < self.sTime or self.Time > self.eTime:
            value = 0
            value1 = 0
        else:
            dT = (self.Time - self.sTime).total_seconds()
            n = int(dT / self.attrs["resTime"])
            value = self.profile[n]
            dT2 = (self.Time - (self.sTime + datetime.timedelta(seconds=int(n * self.attrs["resTime"])))).total_seconds()
            value1 = self.profile[n] + (self.profile[n+1] - self.profile[n]) * dT2 / self.attrs["resTime"]

        if updateObjectProperties:
            for objName, obj in self.Objects.items():
                if self.valueSettings[objName]['interpolate']:
                    value = value1
                mult = self.valueSettings[objName]['multiplier']
                if self.valueSettings[objName]['normalize']:
                    value = value / self.attrs["max"] * mult
                else:
                    value = value * mult
                obj.SetParameter(self.attrs["units"].decode(), value)
        return value


