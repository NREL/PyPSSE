# Standard imports
import os

# Third-party library imports
import pandas as pd
import numpy as np
import datetime
# Internal imports
from pypsse.modes.abstract_mode import AbstractMode
from pypsse.utils.dc2ac.dc_ac_algorithm import DC2ACconverter

class ProductionCostModel(AbstractMode):
    def __init__(self,psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
        self.time = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self._StartTime = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self.incTime = settings["Simulation"]["Step resolution (sec)"]
        self.convergence_helper = DC2ACconverter(psse, self, settings, raw_data, logger)
        return

    def init(self, bussubsystems):
        super().init(bussubsystems)
        self.initialization_complete = True
        return

    def step(self, dt):
        ierr = self.PSSE.fnsl()
        solved_flag = self.PSSE.solved()
        # check if powerflow completed successfully
        if solved_flag == 0:
            self.time = self.time + datetime.timedelta(seconds=self.incTime)
            return 0
        else:
            self.convergence_helper.run()
            if not self.convergence_helper.has_converged:   
                self.logger.error(f'Error code {solved_flag} returned from PSSE while running powerflow, please follow \
                                PSSE doumentation to know more about error')
                return 1
            else:
                self.time = self.time + datetime.timedelta(seconds=self.incTime)
                return 0
                

    def reload(self):
        pass
    
    def resolveStep(self, t):
        ierr = self.PSSE.fnsl()
        solved_flag = self.PSSE.solved()
        if solved_flag > 0:
            self.convergence_helper.run()
            if not self.convergence_helper.has_converged:
                raise Exception(f'Error code {solved_flag} returned from PSSE while running powerflow, please follow \
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
