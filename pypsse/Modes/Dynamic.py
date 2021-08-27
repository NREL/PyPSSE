from pypsse.Modes.naerm_constants import naerm_decorator, DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.Modes.abstract_mode import AbstractMode
from pypsse.common import MACHINE_CHANNELS
import numpy as np
import datetime
import os

class Dynamic(AbstractMode):

    def __init__(self,psse, dyntools, settings, export_settings, logger, subsystem_buses):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses)
        self.time = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        self.incTime = settings["Simulation"]["Step resolution (sec)"]
        self._StartTime = datetime.datetime.strptime(settings["Simulation"]["Start time"], "%m/%d/%Y %H:%M:%S")
        return

    def init(self, bus_subsystems):
        super().init(bus_subsystems)

        # if len(self.settings["Simulation"]["Setup files"]):
        #     ierr = None



        if len(self.settings["Simulation"]["Rwm file"]):
            self.PSSE.mcre([1, 0], self.rwn_file)

        self.PSSE.fnsl([0, 0, 0, 1, 0, 0, 0, self._i])

        for f in self.settings["Simulation"]["Setup files"]:
            setup_path = os.path.join(self.settings["Simulation"]["Project Path"], 'Case_study', f)
            ierr = self.PSSE.runrspnsfile(setup_path)
            if ierr:
                raise Exception('Error running setup file "{}"'.format(setup_path))
            else:
                self.logger.debug('Setup file {} sucessfully run'.format(setup_path))

        #self.convert_load()

        self.PSSE.bsysinit(1)
        self.PSSE.bsys(1, 0, [0.0, 0.0], 0, [], 1, [38950], 0, [], 0, [])
        self.PSSE.bsysadd(1, 0, [0.0, 0.0], 0, [], 1, [38951], 0, [], 0, [])
        self.PSSE.bsysadd(1, 0, [0.0, 0.0], 0, [], 1, [22834], 0, [], 0, [])
        self.PSSE.bsysadd(1, 0, [0.0, 0.0], 0, [], 1, [24659], 0, [], 0, [])
        self.PSSE.bsysadd(1, 0, [0.0, 0.0], 0, [], 1, [24658], 0, [], 0, [])
        self.PSSE.gnet(1, 0)
        self.PSSE.fdns([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.fdns([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.fnsl([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.fnsl([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.fdns([1, 1, 0, 1, 1, 0, 0, 0])
        self.PSSE.switched_shunt_chng_4(73525, [self._i, self._i, self._i, self._i, self._i, self._i, self._i, self._i,
                                                0, self._i, self._i, self._i, self._i],
                                        [self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f,
                                         self._f, self._f, self._f], self._s)
        self.PSSE.fnsl([1, 1, 1, 1, 1, 0, 0, 0])
        self.PSSE.fnsl([1, 1, 1, 1, 1, 0, 0, 0])
        self.PSSE.fnsl([1, 1, 1, 1, 1, 0, 0, 0])
        self.PSSE.fnsl([1, 1, 1, 1, 1, 0, 0, 0])
        self.PSSE.fdns([1, 1, 1, 1, 1, 0, 0, 0])
        self.PSSE.fdns([1, 1, 1, 1, 1, 0, 0, 0])

        self.PSSE.cong(0)
        # Solve for dynamics
        self.PSSE.ordr(0)
        self.PSSE.fact()
        self.PSSE.tysl(0)
        self.PSSE.tysl(0)
        #self.PSSE.save(self.study_case_path.split('.')[0] + ".sav")
        self.logger.debug('Loading dynamic model....')
        self.PSSE.dynamicsmode(1)
        ierr = self.PSSE.dyre_new([1, 1, 1, 1], self.dyr_path, r"""conec""",r"""conet""",r"""compile""")

        self.PSSE.dynamics_solution_param_2([60, self._i, self._i, self._i, self._i, self._i, self._i, self._i],
                                            [0.4, self._f, 0.0033333, self._f, self._f, self._f, self._f, self._f])

        #self.PSSE.snap([1246543, 276458, 1043450, 452309, 0], snpFilePath)

        if ierr:
            raise Exception('Error loading dynamic model file "{}". Error code - {}'.format(self.dyr_path, ierr))
        else:
            self.logger.debug('Dynamic file {} sucessfully loaded'.format(self.dyr_path))

        if self.export_settings["Export results using channels"]:
            self.setup_channels()

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

        # Load user defined models
        for mdl in self.settings["Simulation"]["User models"]:
            dll_path = os.path.join(self.settings["Simulation"]["Project Path"], 'Case_study', mdl)
            self.PSSE.addmodellibrary(dll_path)
            self.logger.debug('User defined library added: {}'.format(mdl))
        # Load flow settings
        self.PSSE.fdns([0, 0, 0, 1, 1, 0, 99, 0])
        # initialize
        iErr = self.PSSE.strt_2([1, self.settings["Generators"]["Missing machine model"]], self.outx_path)
        if iErr:
            self.initialization_complete = False
            raise Exception(f'Dynamic simulation failed to successfully initialize. Error code - {iErr}')
        else:
            self.initialization_complete = True
            self.logger.debug('Dynamic simulation initialization sucess!')
        # get load info for the sub system
        self.load_info = self.get_load_indices(bus_subsystems)

        snp_path = os.path.join(
            self.settings["Simulation"]["Project Path"],
            'Case_study',
            self.settings["Simulation"]["Snp file"]
        )
        #self.PSSE.snap(sfile=snp_path)

        self.logger.debug('pyPSSE initialization complete!')

        return self.initialization_complete

    def step(self, t):
        self.time = self.time + datetime.timedelta(seconds=self.incTime)
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
                    'Load ID' : load_data[0,i],
                    'Bus name' : load_data[1,i],
                    'Bus name (ext)' : load_data[2,i],
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
        #print(results)
        return results
