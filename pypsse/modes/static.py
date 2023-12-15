# Standard imports
import os

# Internal imports
from pypsse.modes.abstract_mode import AbstractMode


class Static(AbstractMode):
    def __init__(self, psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
        self.time = settings.simulation.start_time
        self._StartTime = settings.simulation.start_time
        self.incTime = settings.simulation.simulation_step_resolution

    def init(self, bussubsystems):
        super().init(bussubsystems)
        self.initialization_complete = True

    def step(self):
        ierr = self.PSSE.fnsl()
        # check if powerflow completed successfully
        if ierr == 0:
            self.time = self.time + self.incTime
        else:
            msg = f"Error code {ierr} returned from PSSE while running powerflow, please follow \
                            PSSE doumentation to know more about error"
            raise Exception(msg)

    def resolve_step(self):
        ierr = self.PSSE.fnsl()
        if ierr > 0:
            msg = f"Error code {ierr} returned from PSSE while running powerflow, please follow \
                                        PSSE doumentation to know more about error"
            raise Exception(msg)

    def get_time(self):
        return self.time

    def get_total_seconds(self):
        return (self.time - self._StartTime).total_seconds()

    def get_step_size_cec(self):
        return self.settings.simulation.simulation_step_resolution.total_seconds()

    def export(self):
        self.logger.debug("Starting export process. Can take a few minutes for large files")
        excelpath = os.path.join(self.export_path, self.settings["Excel file"])
        achnf = self.dyntools.CHNF(self.outx_path)
        achnf.xlsout(channels="", show=False, xlsfile=excelpath, outfile="", sheet="Sheet1", overwritesheet=True)
        self.logger.debug(f"{self.settings.export.excel_file} exported")
