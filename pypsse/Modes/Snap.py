from pypsse.Modes.naerm_constants import naerm_decorator, DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.Modes.abstract_mode import AbstractMode
import numpy as np
import datetime
import os

class Snap(AbstractMode):

    def __init__(self,psse, dyntools, settings, export_settings, logger, subsystem_buses):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses)
        self.time = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self._StartTime = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self.incTime = settings["Simulation"]["Step resolution (sec)"]
        return

    def init(self, bus_subsystems):
        super().init(bus_subsystems)
        ierr = self.PSSE.case(self.study_case_path)
        assert ierr == 0, "error={}".format(ierr)
        ierr = self.PSSE.rstr(self.snp_file)
        assert ierr == 0, "error={}".format(ierr)
        ierr = self.PSSE.strt_2([0, 1],  self.outx_path)

        if ierr==1:
            self.PSSE.cong(0)
            ierr = self.PSSE.strt_2([0, 1],  self.outx_path)
            assert ierr == 0, "error={}".format(ierr)
        
        elif ierr >1:
            raise Exception("Error starting simulation")
            

        for i, bus in enumerate(self.sub_buses):
            self.bus_freq_channels[bus] = i+1
            self.PSSE.bus_frequency_channel([i+1, int(bus)], "")
            self.logger.info(f"Frequency for bus {bus} added to channel {i+1}")

        self.logger.debug('pyPSSE initialization complete!')
        self.initialization_complete = True
        return self.initialization_complete


    def step(self, t):
        self.time = self.time + datetime.timedelta(seconds=self.incTime)
        return self.PSSE.run(0, t, 1, 1, 1)

    def get_load_indices(self, bus_subsystems):
        all_bus_ids = {}
        for id in bus_subsystems.keys():
            load_info = {}
            ierr, load_data = self.PSSE.aloadchar(id, 1, ['ID', 'NAME', 'EXNAME'])
            load_data = np.array(load_data)
            ierr, bus_data = self.PSSE.aloadint(id, 1, ['NUMBER'])
            bus_data = bus_data[0]
            for i, bus_id in enumerate(bus_data):
                load_info[bus_id] = {
                    'Load ID': load_data[0, i],
                    'Bus name': load_data[1, i],
                    'Bus name (ext)': load_data[2, i],
                }
            all_bus_ids[id] = load_info
        return all_bus_ids

    def getTime(self):
        return self.time

    def GetTotalSeconds(self):
        return (self.time - self._StartTime).total_seconds()

    def GetStepSizeSec(self):
        return self.settings["Simulation"]["Step resolution (sec)"]

    def convert_load(self, busSubsystem= None):
        if self.settings['Loads']['Convert']:
            P1 = self.settings['Loads']['active_load']["% constant current"]
            P2 = self.settings['Loads']['active_load']["% constant admittance"]
            Q1 = self.settings['Loads']['reactive_load']["% constant current"]
            Q2 = self.settings['Loads']['reactive_load']["% constant admittance"]
            if busSubsystem:
                self.PSSE.conl(busSubsystem, 0, 1, [0, 0], [P1, P2, Q1, Q2]) # initialize for load conversion.
                self.PSSE.conl(busSubsystem, 0, 2, [0, 0], [P1, P2, Q1, Q2]) # convert loads.
                self.PSSE.conl(busSubsystem, 0, 3, [0, 0], [P1, P2, Q1, Q2]) # postprocessing housekeeping.
            else:
                self.PSSE.conl(0, 1, 1, [0, 0], [P1, P2, Q1, Q2]) # initialize for load conversion.
                self.PSSE.conl(0, 1, 2, [0, 0], [P1, P2, Q1, Q2]) # convert loads.
                self.PSSE.conl(0, 1, 3, [0, 0], [P1, P2, Q1, Q2]) # postprocessing housekeeping.


    @naerm_decorator
    def read_subsystems(self, quantities, subsystem_buses, ext_string2_info={}, mapping_dict={}):
        print(ext_string2_info, mapping_dict)
        results = super(Snap, self).read_subsystems(
            quantities,
            subsystem_buses,
            mapping_dict=mapping_dict,
            ext_string2_info=ext_string2_info
        )
        """ Add """
        for class_name, vars in quantities.items():
            if class_name in dyn_only_options:
                for v in vars:
                    if v in DYNAMIC_ONLY_PPTY[class_name]:
                        for funcName in dyn_only_options[class_name]:
                            if v in dyn_only_options[class_name][funcName]:
                                con_ind = dyn_only_options[class_name][funcName][v]
                                for bus in subsystem_buses:
                                    if class_name == "Loads":
                                        ierr = self.PSSE.inilod(int(bus))
                                        ierr, ld_id = self.PSSE.nxtlod(int(bus))
                                        irr, con_index = getattr(self.PSSE, funcName)(int(bus), ld_id, 'CHARAC', 'CON')
                                        act_con_index = con_index + con_ind
                                        irr, value = self.PSSE.dsrval('CON', act_con_index)
                                        #print(class_name, funcName, bus, ld_id, con_index, con_num, v, value)
                                        res_base = f"{class_name}_{v}"
                                        if res_base not in results:
                                            results[res_base] = {}
                                        obj_name = f"{bus}_{ld_id}"
                                        results[res_base][obj_name] = value
            else:
                self.logger.warning("Extend function 'read_subsystems' in the Snap class (Snap.py)")

        return results
