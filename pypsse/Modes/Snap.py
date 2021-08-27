from pypsse.Modes.naerm_constants import naerm_decorator, DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.Modes.abstract_mode import AbstractMode
from pypsse.common import MACHINE_CHANNELS
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
            

        # for i, bus in enumerate(self.sub_buses):
        #     self.bus_freq_channels[bus] = i+1
        #     self.PSSE.bus_frequency_channel([i+1, int(bus)], "")
        #     self.logger.info(f"Frequency for bus {bus} added to channel {i+1}")

        self.PSSE.delete_all_plot_channels()

        self.channel_map = {}
        self.chnl_idx = 1

        self.setup_bus_channels(
            [14203, 14303, 14352, 15108, 15561, 17604, 17605, 37102, 37124, 37121],
            ["voltage_and_angle", "frequency"])
        self.setup_load_channels([
            ('AP', 14303), ('AP', 14352), ('SR', 15108), ('1', 15561), ('AE', 17604),
            ('AE', 17605), ('1', 37102), ('1', 37124), ('1', 37121)
        ])
        self.setup_machine_channels(
            machines=[
                ('1', 15140), ('1', 15252), ('7', 17189), ('1', 37102), ('1', 37121), ('1', 37124)
            ],
            properties=["PELEC", "QELEC", "SPEED"]
        )

        self.logger.debug('pyPSSE initialization complete!')
        self.initialization_complete = True
        return self.initialization_complete

    def setup_machine_channels(self, machines, properties):
        for i, qty in enumerate(properties):
            if qty not in self.channel_map:
                nqty = f"MACHINE_{qty}"
                self.channel_map[nqty] = {}
            for mch, b in machines:
                if qty in MACHINE_CHANNELS:
                    self.channel_map[nqty][f"{b}_{mch}"] = [self.chnl_idx]
                    chnl_id = MACHINE_CHANNELS[qty]
                    self.logger.info(f"{qty} for machine {b}_{mch} added to channel {self.chnl_idx}")
                    self.PSSE.machine_array_channel([self.chnl_idx, chnl_id, int(b)], mch, "")
                    self.chnl_idx += 1
        return


    def setup_bus_channels(self, buses, properties):
        for i, qty in enumerate(properties):
            if qty not in self.channel_map:
                self.channel_map[qty] = {}
            for j, b in enumerate(buses):
                if qty == "frequency":
                    self.channel_map[qty][b] = [ self.chnl_idx]
                    self.PSSE.bus_frequency_channel([ self.chnl_idx, int(b)], "")
                    self.logger.info(f"Frequency for bus {b} added to channel { self.chnl_idx}")
                    self.chnl_idx += 1
                elif qty == "voltage_and_angle":
                    self.channel_map[qty][b] = [ self.chnl_idx,  self.chnl_idx+1]
                    self.PSSE.voltage_and_angle_channel([ self.chnl_idx, -1, -1, int(b)], "")
                    self.logger.info(f"Voltage and angle for bus {b} added to channel {self.chnl_idx} and {self.chnl_idx+1}")
                    self.chnl_idx += 2

    def setup_load_channels(self, loads):
        if "LOAD_P" not in self.channel_map:
            self.channel_map["LOAD_P"] = {}
            self.channel_map["LOAD_Q"] = {}
        for ld, b in loads:
            self.channel_map["LOAD_P"][f"{b}_{ld}"] = [self.chnl_idx]
            self.channel_map["LOAD_Q"][f"{b}_{ld}"] = [self.chnl_idx + 1]
            self.PSSE.load_array_channel([self.chnl_idx, 1, int(b)], ld, "")
            self.PSSE.load_array_channel([self.chnl_idx + 1, 2, int(b)], ld, "")
            self.logger.info(f"P and Q for load {b}_{ld} added to channel {self.chnl_idx} and {self.chnl_idx + 1}")
            self.chnl_idx += 2

    def step(self, t):
        self.time = self.time + datetime.timedelta(seconds=self.incTime)
        self.xTime = 0
        return self.PSSE.run(0, t, 1, 1, 1)


    def poll_channels(self):
        results = {}
        for ppty , bDict in self.channel_map.items():
            ppty_new = ppty.split("_and_")
            for b, indices in bDict.items():
                for n, idx in zip(ppty_new, indices):
                    if "_" not in n:
                        nName = f"BUS_{n}"
                    else:
                        nName = n
                    if nName not in results:
                        results[nName] = {}
                    ierr, value = self.PSSE.chnval(idx)
                    if value is None:
                        value = -1
                    results[nName][b] = value
        return results

    def resolveStep(self, t):
        self.xTime += 1
        return self.PSSE.run(0, t + self.xTime * self.incTime / 1000.0, 1, 1, 1)


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
        #print(ext_string2_info, mapping_dict)
        results = super(Snap, self).read_subsystems(
            quantities,
            subsystem_buses,
            mapping_dict=mapping_dict,
            ext_string2_info=ext_string2_info
        )

        poll_results = self.poll_channels()
        results.update(poll_results)
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
                                        if ld_id is not None:
                                            irr, con_index = getattr(self.PSSE, funcName)(int(bus), ld_id, 'CHARAC',
                                                                                          'CON')
                                            if con_index is not None:
                                                act_con_index = con_index + con_ind
                                                irr, value = self.PSSE.dsrval('CON', act_con_index)
                                                # print(class_name, funcName, bus, ld_id, con_index, con_num, v, value)
                                                res_base = f"{class_name}_{v}"
                                                if res_base not in results:
                                                    results[res_base] = {}
                                                obj_name = f"{bus}_{ld_id}"
                                                results[res_base][obj_name] = value
            else:
                self.logger.warning("Extend function 'read_subsystems' in the Snap class (Snap.py)")
        print(results)

        return results
