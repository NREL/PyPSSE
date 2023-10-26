from pypsse.modes.constants import converter, DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.modes.abstract_mode import AbstractMode
from pypsse.utils.dynamic_utils import DynamicUtils
from pypsse.common import MACHINE_CHANNELS
import pandas as pd
import numpy as np
import datetime
import os

class Snap(AbstractMode, DynamicUtils):

    def __init__(self,psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
        self.time = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self._StartTime = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self.incTime = settings["Simulation"]["Step resolution (sec)"]
        self.init(subsystem_buses)
        return

    def init(self, bus_subsystems):
        super().init(bus_subsystems)

        self.iter_const = 100.0
        self.xTime = 0

        ierr = self.PSSE.case(self.study_case_path)
        assert ierr == 0, "error={}".format(ierr)
        ierr = self.PSSE.rstr(self.snp_file)
        assert ierr == 0, "error={}".format(ierr)
        ierr = self.PSSE.strt_2([0, 1],  self.outx_path)

        self.disable_load_models_for_coupled_buses()
        self.disable_generation_for_coupled_buses()

        #self.save_model()

        if ierr==1:
            self.PSSE.cong(0)
            ierr = self.PSSE.strt_2([0, 1],  self.outx_path)
            assert ierr == 0, "error={}".format(ierr)
        
        elif ierr >1:
            raise Exception("Error starting simulation")

        if self.settings["HELICS"]["Cosimulation mode"]:
            if self.settings["HELICS"]["Iterative Mode"]:
                sim_step = self.settings["Simulation"]["PSSE solver timestep (sec)"] / self.iter_const
            else:
                sim_step = self.settings["Simulation"]["PSSE solver timestep (sec)"]
        else:
            sim_step = self.settings["Simulation"]["PSSE solver timestep (sec)"]

        for mdl in self.settings["Simulation"]["User models"]:
            dll_path = os.path.join(self.settings["Simulation"]["Project Path"], 'Case_study', mdl)
            self.PSSE.addmodellibrary(dll_path)
            self.logger.debug('User defined library added: {}'.format(mdl))

        self.PSSE.dynamics_solution_param_2(
            [60, self._i, self._i, self._i, self._i, self._i, self._i, self._i],
            [0.4, self._f, sim_step, self._f, self._f, self._f, self._f, self._f]
        )


        self.PSSE.delete_all_plot_channels()

        self.channel_map = {}
        self.chnl_idx = 1
        for method_type, settings in self.export_settings["channel_setup"].items():
            for setting in settings:
                if method_type == "buses":
                    self.setup_bus_channels(setting["list"], setting["properties"])
                elif method_type == "loads":
                    load_list = [[x, int(y)] for x, y in setting["list"]]
                    self.setup_load_channels(load_list)
                elif method_type == "machines":
                    machine_list = [[x, int(y)] for x, y in setting["list"]]
                    self.setup_machine_channels(machine_list, setting["properties"])

        self.logger.debug('pyPSSE initialization complete!')
        self.initialization_complete = True
        return self.initialization_complete

    def disable_generation_for_coupled_buses(self):
        if self.settings['HELICS']['Cosimulation mode'] and self.settings['HELICS']["Disable_generation_on_coupled_buses"]:
            sub_data = pd.read_csv(
                os.path.join(
                    self.settings["Simulation"]["Project Path"], 'Settings',
                    self.settings["HELICS"]["Subscriptions file"]
                )
            )
            sub_data = sub_data[sub_data['element_type'] == 'Load']
            generators = {}
            for ix, row in sub_data.iterrows():
                bus = row['bus']
                for gen_bus, gen_id in self.raw_data.generators:
                    if gen_bus not in generators:
                        generators[bus] = [gen_id]
                    else:
                        generators[bus].append(gen_id)

            for bus_id, machines in generators.items():
                for machine in machines:
                    intgar = [0, self._i, self._i, self._i, self._i, self._i]
                    realar = [
                        self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f,
                        self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f
                    ]
                    self.PSSE.machine_chng_2(bus_id, machine, intgar, realar)
                    self.logger.info(f"Machine disabled: {bus_id}_{machine}")
        return

    def disable_load_models_for_coupled_buses(self):
        if self.settings['HELICS']['Cosimulation mode']:
            sub_data = pd.read_csv(
                os.path.join(
                    self.settings["Simulation"]["Project Path"], 'Settings',
                    self.settings["HELICS"]["Subscriptions file"]
                )
            )
            sub_data = sub_data[sub_data['element_type'] == 'Load']

            self.psse_dict = {}
            for ix, row in sub_data.iterrows():
                bus = row['bus']
                load = row['element_id']
                ierr = self.PSSE.ldmod_status(0, int(bus), str(load), 1, 0)
                self.logger.error(f"Dynamic model for load {load} connected to bus {bus} has been disabled")

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
        return self.PSSE.run(0, t + self.xTime * self.incTime / self.iter_const, 1, 1, 1)


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


    @converter
    def read_subsystems(self, quantities, subsystem_buses, ext_string2_info={}, mapping_dict={}):

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

                                                res_base = f"{class_name}_{v}"
                                                if res_base not in results:
                                                    results[res_base] = {}
                                                obj_name = f"{bus}_{ld_id}"
                                                results[res_base][obj_name] = value
            else:
                self.logger.warning("Extend function 'read_subsystems' in the Snap class (Snap.py)")

        return results
