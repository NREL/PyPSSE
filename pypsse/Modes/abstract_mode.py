# Standard imports
import os

class AbstractMode:

    def __init__(self, psse, dyntools, settings, export_settings, logger):
        self.PSSE = psse
        self.logger = logger
        self.dyntools = dyntools
        self.settings = settings
        self.export_settings = export_settings
        self.func_options = {
                'Buses': {
                    'busdat': ['BASE', 'PU', 'KV', 'ANGLE', 'ANGLED', 'NVLMHI', 'NVLMLO', 'EVLMHI', 'EVLMLO'],
                    'busdt2': ['TOTAL', 'FX_TOTAL', 'SC_TOTAL'],
                },
                'Branches': {
                    'brndat': ['RATEn', 'RATEA', 'RATEB', 'RATEC', 'RATE', 'LENGTH', 'CHARG', 'CHARGZ', 'FRACT1', 'FRACT2',
                               'FRACT3', 'FRACT4'],
                    'brndt2': ['RX', 'ISHNT', 'JSHNT', 'RXZ', 'ISHNTZ', 'JSHNTZ', 'LOSSES', 'O_LOSSES'],
                    'brnmsc': ['MVA', 'AMPS', 'PUCUR', 'CURANG', 'P', 'O_P', 'Q', 'O_Q', 'PLOS', 'O_PLOS', 'QLOS', 'O_QLOS'],
                },
                'Induction_generators': {
                    'inddt1': ["MBASE", "RATEKV", "PSET", "RA", "XA", "R1", "X1", "R2", "X2", "X3", "E1", "SE1", "E2",
                               "SE2", "IA1", "IA2", "XAMULT", "TRQA", "TRQB", "TRQD", "TRQE", "H", "IRATIO", "ROVERX",
                               "RZERO", "XZERO", "RGRND", "XGRND", "P", "O_P", "Q", "O_Q", "MVA", "O_MVA", "SLIP"],
                    'inddt2': ['ZA', 'Z1', 'Z2', 'ZZERO', 'ZGRND', 'PQ', 'O_PQ'],
                },
                'Loads': {
                    'loddt2': ['MVA', 'IL', 'YL', 'TOTAL', 'YNEG', 'YZERO'],
                },
                'Machines': {
                    'macdat': ["QMAX", "O_QMAX", "QMIN", "O_QMIN", "PMAX", "O_PMAX", "PMIN", "O_PMIN", "MBASE", "MVA",
                               "O_MVA", "P", "O_P", "Q", "O_Q", "PERCENT", "GENTAP", "VSCHED", "WPF", "RMPCT", "RPOS",
                               "XSUBTR", "XTRANS", "XSYNCH"],
                    'macdt2': ["PQ", "O_PQ", "ZSORCE", "XTRAN", "ZPOS", "ZNEG", "ZZERO", "ZGRND"]
                },
                'Fixed_shunts': {
                    'fxsdt2': ["PQ", "O_PQ", "ZSORCE", "XTRAN", "ZPOS", "ZNEG", "ZZERO", "ZGRND"]
                },
                'Switched_shunts': {
                    'swsdt1': ["VSWHI", "VSWLO", "RMPCT", "BINIT", "O_BINIT"],
                },
                'Transformers': {
                    'xfrdat': ['RATIO', 'RATIO2', 'ANGLE', 'RMAX', 'RMIN', 'VMAX', 'VMIN', 'STEP', 'CR', 'CX', 'CNXANG',
                                'SBASE1', 'NOMV1', 'NOMV2', 'NOMV2', 'GMAGNT', 'BMAGNT', 'RG1', 'XG1', 'R01', 'X01', 'RG2',
                                'XG2', 'R02', 'X02', 'RNUTRL', 'XNUTRL'],
                    'tr3dt2': ['RX1-2', 'RX2-3', 'RX3-1', 'YMAGNT', 'ZG1', 'Z01', 'ZG2', 'Z02', 'ZG3', 'Z03', 'ZNUTRL' ]
                }

            }
        self.initialization_complete = False

    def init(self, bus_subsystems):
        self.export_path = os.path.join(self.settings["Simulation"]["Project Path"], 'Exports')
        self.study_case_path = os.path.join(
            self.settings["Simulation"]["Project Path"], 'Case_study', self.settings["Simulation"]["Case study"]
        )
        self.dyr_path = os.path.join(
            self.settings["Simulation"]["Project Path"], 'Case_study', self.settings["Simulation"]["Dyr file"]
        )
        self.outx_path = os.path.join(
            self.settings["Simulation"]["Project Path"], 'Case_study', self.settings["Export_settings"]["Outx file"]
        )
        self.snp_file = os.path.join(
            self.settings["Simulation"]["Project Path"], 'Case_study', self.settings["Simulation"]["Snp file"]
        )
        self.rwn_file = os.path.join(
            self.settings["Simulation"]["Project Path"], 'Case_study', self.settings["Simulation"]["Rwm file"]
        )
        self.ext = self.study_case_path.split('.')[1]

        if self.settings["Logging"]["Disable PSSE logging"]:
            self.disable_logging()

    def step(self, dt):
        return

    def resolveStep(self):
        return

    def export(self):
        self.logger.debug('Starting export process. Can take a few minutes for large files')
        excelpath = os.path.join(self.export_path, self.settings["Export_settings"]["Excel file"])
        achnf = self.dyntools.CHNF(self.outx_path)
        achnf.xlsout(channels='', show=False, xlsfile=excelpath, outfile='', sheet='Sheet1', overwritesheet=True)
        self.logger.debug('{} export to {}'.format(self.settings["Export_settings"]["Excel file"], self.export_path))

    def disable_logging(self):
        self.PSSE.progress_output(islct=6,  filarg='', options=[0, 0])
        self.PSSE.prompt_output(islct=6, filarg='', options=[0, 0])
        self.PSSE.report_output(islct=6, filarg='', options=[0, 0])

    def setup_channels(self):
        import pypsse.Channel_map as Channel_map
        for channel, add in self.export_settings["Channels"].items():
            if add:
                channelID = Channel_map.channel_map[channel]
                self.logger.debug('"{}" added to the channel file'.format(channel))
                self.PSSE.chsb(0, 1, [-1, -1, -1, 1, channelID, 0])

    def read_subsystems(self,quantities, subsystem_buses):
        results = {}
        for class_name, vars in quantities.items():
            if class_name in self.func_options:
                funcs = self.func_options[class_name]
                for v in vars:
                    for func_name, settinsgs in funcs.items():
                        q = "{}_{}".format(class_name, v)
                        for b in subsystem_buses:
                            if func_name in ['busdat', 'busdt2']:
                                if func_name == "busdat":
                                    irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                    results =self.add_result(results, q, val, b)
                                elif func_name == "busdt2":
                                    irr, val = getattr(self.PSSE, func_name)(int(b), v, 'ACT')
                                    results =self.add_result(results, q, val, b)
                            elif func_name == "loddt2":
                                id = ''
                                ierr = self.PSSE.inilod(int(b))
                                while id != None:
                                    ierr, id = self.PSSE.nxtlod(int(b))
                                    irr, val = getattr(self.PSSE, func_name)(int(b), id, v, 'ACT')
                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                            elif func_name in ["macdat", 'macdt2']:
                                id = ''
                                ierr = self.PSSE.inimac(int(b))
                                while id != None:
                                    ierr, id = self.PSSE.nxtmac(int(b))
                                    irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                            elif func_name == 'fxsdt2':
                                id = ''
                                ierr = self.PSSE.inimac(int(b))
                                while id != None:
                                    ierr, id = self.PSSE.nxtfxs(int(b))
                                    irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                            elif func_name == 'swsdt1':
                                irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                results = self.add_result(results, q, val, b)
                            elif func_name in ['brndat', 'brndt2', 'brnmsc']:
                                b1 = ''
                                ierr = self.PSSE.inibrx(int(b), 3)
                                while b1 != None:
                                    ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                    irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), ickt, v)
                                    results = self.add_result(results, q, val, b)
                            elif func_name in ['xfrdat', 'tr3dt2']:
                                b1 = ''
                                ierr = self.PSSE.inibrx(int(b), 3)
                                while b1 != None:
                                    ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                    if func_name == 'xfrdat':
                                        irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), '1 ', v)
                                        results = self.add_result(results, q, val, b)
                                b1 = ''
                                ierr = self.PSSE.inibrx(int(b), 3)
                                while b1 != None:
                                    ierr, b1, b2, ickt = self.PSSE.nxtbrn3(int(b))
                                    if func_name == 'xfrdat':
                                        irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), int(b2), ickt, v)
                                        results = self.add_result(results, q, val, b)
        return results


    def read(self, quantities, raw_data):
        results = {}
        for class_name, vars in quantities.items():
            if class_name in self.func_options:
                funcs = self.func_options[class_name]
                for v in vars:
                    for func_name, settinsgs in funcs.items():
                        q = "{}_{}".format(class_name, v)
                        if func_name in ['busdat', 'busdt2']:
                            for b in raw_data.buses:
                                if func_name == "busdat":
                                    irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                    results =self.add_result(results, q, val, b)
                                elif func_name == "busdt2":
                                    irr, val = getattr(self.PSSE, func_name)(int(b), v, 'ACT')
                                    results =self.add_result(results, q, val, b)
                        elif func_name == "loddt2":
                            for b, id in raw_data.loads:
                                ierr = self.PSSE.inilod(int(b))
                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v, 'ACT')
                                results =self.add_result(results, q, val,  '{}_{}'.format(id, b))
                        elif func_name in ["macdat", 'macdt2']:
                            for b, id in raw_data.generators:
                                ierr = self.PSSE.inimac(int(b))
                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                        elif func_name == 'fxsdt2':
                            for b, id in raw_data.fixed_stunts:
                                ierr = self.PSSE.inimac(int(b))
                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                        elif func_name == 'swsdt1':
                            for b in raw_data.switched_shunt:
                                irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                results = self.add_result(results, q, val, b)
                        if func_name in ['brndat', 'brndt2', 'brnmsc']:
                            for b, b1 in raw_data.branches:
                                irr, val = getattr(self.PSSE, func_name)(int(b),int(b1), '1 ', v)
                                results = self.add_result(results, q, val, b)
                        if func_name in ['xfrdat', 'tr3dt2']:
                            for b, b1, b2 in raw_data.transformers:
                                if func_name == 'xfrdat':
                                    if int(b2.replace(' ', '')) == 0:
                                        irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), '1 ', v)
                                        results = self.add_result(results, q, val, b)
                                elif func_name == 'xfrdat':
                                    if int(b2.replace(' ', '')) != 0:
                                        irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), int(b2), '1 ', v)
                                        results = self.add_result(results, q, val, b)

        return results

    def add_result(self, results_dict, class_name, value, label):
        if value:
            if class_name not in results_dict:
                results_dict[class_name] = {}
            results_dict[class_name][label] = value
        return results_dict

    def update_object(self, dType, bus, id, values):
        if dType == "Load":
            ierr = self.PSSE.load_data_5(ibus=int(bus), id=id, **values)
        elif dType == "Induction_machine":
            ierr = self.PSSE.induction_machine_data(ibus=int(bus), id=id, **values)
        elif dType == "Machine":
            ierr = self.PSSE.machine_data_2(i=int(bus), id=id, **values)
        elif dType == "Plant":
            ierr = self.PSSE.plant_data_4(ibus=int(bus), inode=id, **values)
        else:
            ierr = 0

        if ierr == 0:
            self.logger.debug(f"Profile Manager: {dType} '{id}' on bus '{bus}' has been updated.")
        else:
            self.logger.error(f"Profile Manager: Error updating {dType} '{id}' on bus '{bus}'.")