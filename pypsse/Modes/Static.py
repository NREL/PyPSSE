# Standard imports
import os

# Third-party library imports
import pandas as pd
import numpy as np
import datetime
# Internal imports
from pypsse.Modes.abstract_mode import AbstractMode

class Static(AbstractMode):
    def __init__(self,psse, dyntools, settings, export_settings, logger, subsystem_buses):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses)
        self.time = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self._StartTime = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self.incTime = settings["Simulation"]["Step resolution (sec)"]
        return

    def init(self, bussubsystems):
        super().init(bussubsystems)
        self.initialization_complete = True
        return

    def step(self, dt):
        ierr = self.PSSE.fnsl()
        # check if powerflow completed successfully
        if ierr == 0:
            self.time = self.time + datetime.timedelta(seconds=self.incTime)
        else:
            raise Exception(f'Error code {ierr} returned from PSSE while running powerflow, please follow \
                            PSSE doumentation to know more about error')

    def resolveStep(self):
        ierr = self.PSSE.fnsl()
        if ierr > 0:
            raise Exception(f'Error code {ierr} returned from PSSE while running powerflow, please follow \
                                        PSSE doumentation to know more about error')
    def getTime(self):
        return self.time

    def GetTotalSeconds(self):
        return (self.time - self._StartTime).total_seconds()

    def GetStepSizeSec(self):
        return self.settings["Simulation"]["Step resolution (sec)"]

    def export(self):
        self.logger.debug('Starting export process. Can take a few minutes for large files')
        excelpath = os.path.join(self.export_path, self.settings["Excel file"])
        achnf = self.dyntools.CHNF(self.outx_path)
        achnf.xlsout(channels='', show=False, xlsfile=excelpath, outfile='', sheet='Sheet1', overwritesheet=True)
        self.logger.debug('{} export to {}'.format(self.settings["Simulation"]["Excel file"], self.export_path))
