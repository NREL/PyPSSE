from pypsse.modes.constants import converter, DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.models import SimulationSettings, ExportSettings
from pypsse.modes.abstract_mode import AbstractMode
from pypsse.common import MACHINE_CHANNELS
from pypsse.utils.dynamic_utils import DynamicUtils
import pandas as pd
import numpy as np
import datetime
import os

class Dynamic(AbstractMode, DynamicUtils):

    def __init__(self,psse, dyntools, settings:SimulationSettings, export_settings:ExportSettings, logger, subsystem_buses, raw_data):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
        self.time = settings.simulation.start_time
        self._StartTime = settings.simulation.start_time
        self.incTime = settings.simulation.simulation_step_resolution

        self.init({})
        return

    def init(self, bus_subsystems):
        super().init(bus_subsystems)
        self.iter_const = 100.0

        if self.settings.simulation.rwm_file:
            self.PSSE.mcre([1, 0], self.rwn_file)

        self.PSSE.fnsl([0, 0, 0, 1, 0, 0, 0, self._i])

        self.load_setup_files()
        self.convert_load()
        
        self.PSSE.gnet(1, 0)
        self.PSSE.fdns([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.fnsl([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.cong(0)
        # Solve for dynamics
        self.PSSE.ordr(0)
        self.PSSE.fact()
        self.PSSE.tysl(0)
        self.PSSE.tysl(0)
        #self.PSSE.save(self.study_case_path.split('.')[0] + ".sav")
        dyr_path = self.settings.simulation.dyr_file
        assert dyr_path and dyr_path.exists
        self.logger.debug(f'Loading dynamic model....{dyr_path}')
        self.PSSE.dynamicsmode(1)
        ierr = self.PSSE.dyre_new([1, 1, 1, 1], str(dyr_path), r"""conec""",r"""conet""",r"""compile""")

        if self.settings.helics and self.settings.helics.cosimulation_mode:
            if self.settings.helics.iterative_mode:
                sim_step = self.settings.simulation.psse_solver_timestep.total_seconds() / self.iter_const
            else:
                sim_step = self.settings.simulation.psse_solver_timestep.total_seconds()
        else:
            sim_step = self.settings.simulation.psse_solver_timestep.total_seconds()

        ierr = self.PSSE.dynamics_solution_param_2(
            [60, self._i, self._i, self._i, self._i, self._i, self._i, self._i],
            [0.4, self._f, sim_step, self._f, self._f, self._f, self._f, self._f]
        )

        if ierr:
            raise Exception('Error loading dynamic model file "{}". Error code - {}'.format(dyr_path, ierr))
        else:
            self.logger.debug('Dynamic file {} sucessfully loaded'.format(dyr_path))

        self.disable_load_models_for_coupled_buses()

        if self.export_settings["Export results using channels"]:
            self.setup_channels()

        self.PSSE.delete_all_plot_channels()

        #print(self.export_settings["channel_setup"])
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
      

        # Load user defined models
        self.load_user_defined_models()
        
        # Load flow settings
        self.PSSE.fdns([0, 0, 0, 1, 1, 0, 99, 0])
        # initialize
        iErr = self.PSSE.strt_2([
            1, 
            self.settings.generators.missing_machine_model, 
            ], str(self.settings.export.outx_file))
        if iErr:
            self.initialization_complete = False
            raise Exception(f'Dynamic simulation failed to successfully initialize. Error code - {iErr}')
        else:
            self.initialization_complete = True
            self.logger.debug('Dynamic simulation initialization sucess!')
        # get load info for the sub system
        self.load_info = self.get_load_indices(bus_subsystems)

        self.logger.debug('pyPSSE initialization complete!')

        self.xTime = 0

        return self.initialization_complete


    def step(self, t):
        self.time = self.time + self.incTime
        self.xTime = 0
        return self.PSSE.run(0, t, 1, 1, 1)

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

    def resolveStep(self, t):
        err = self.PSSE.run(0, t + self.xTime * self.incTime / self.iter_const, 1, 1, 1)
        self.xTime += 1
        return err

    def getTime(self):
        return self.time

    def GetTotalSeconds(self):
        return (self.time - self._StartTime).total_seconds()

    def GetStepSizeSec(self):
        return self.settings.simulation.simulation_step_resolution.total_seconds()

    @converter
    def read_subsystems(self, quantities, subsystem_buses, ext_string2_info={}, mapping_dict={}):
        results = super(Dynamic, self).read_subsystems(
            quantities,
            subsystem_buses,
            mapping_dict=mapping_dict,
            ext_string2_info=ext_string2_info
        )

        poll_results = self.poll_channels()
        results.update(poll_results)
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
                                            irr, con_index = getattr(self.PSSE, funcName)(int(bus), ld_id, 'CHARAC', 'CON')
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
                self.logger.warning("Extend function 'read_subsystems' in the Dynamic class (Dynamic.py)")
        return results

