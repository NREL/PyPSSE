import numpy as np
import os
class Dynamic:
    func_options = {
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
    def __init__(self,psse, dyntools, settings, export_settings, logger):
        self.PSSE = psse
        self.logger = logger
        self.dyntools = dyntools
        self.settings = settings
        self.export_settings = export_settings
        self.initialization_complete = False
        return

    def init(self, bus_subsystems):
        self.export_path = os.path.join(self.settings["Project Path"], 'Exports')
        study_case_path = os.path.join(self.settings["Project Path"], 'Case_study', self.settings["Case study"])
        dyr_path = os.path.join(self.settings["Project Path"], 'Case_study', self.settings["Dyr file"])
        outx_path = os.path.join(self.settings["Project Path"], 'Case_study', self.settings["Outx file"])
        snp_file = os.path.join(self.settings["Project Path"], 'Case_study', self.settings["Snp file"])
        rwn_file = os.path.join(self.settings["Project Path"], 'Case_study', self.settings["Rwm file"])
        ext = study_case_path.split('.')[1]
        self.outx_path = outx_path
        self.logger.debug('Loading case study....')
        if ext == 'raw':
            ierr = self.PSSE.read(0, study_case_path)
        else:
            ierr = self.PSSE.case(study_case_path)
        if ierr == 3:
            raise Exception('File "{}" not found'.format(study_case_path))
        elif ierr:
            raise Exception('Error loading case study file "{}"'.format(study_case_path))
        else:
            self.logger.debug('Sucess!')

        if self.settings["Disable PSSE logging"]:
            self.disable_logging()

        # buses = [34017, 34020]
        # self.PSSE.bsysinit(0)
        # ierr = self.PSSE.bsys(sid=0, numbus=len(buses), buses=buses)

        if len(self.settings["Setup files"]):
            ierr = None
            for f in self.settings["Setup files"]:
                setup_path = os.path.join(self.settings["Project Path"], 'Case_study', f)
                ierr = self.PSSE.runrspnsfile(setup_path)
                if ierr:
                    raise Exception('Error running setup file "{}"'.format(setup_path))
                else:
                    self.logger.debug('Setup file {} sucessfully run'.format(setup_path))

        else:
            if len(self.settings["Rwm file"]):
                self.PSSE.mcre([1, 0], rwn_file)

            self.convert_load()
            self.PSSE.cong(0)
            # Solve for dynamics
            self.PSSE.ordr(0)
            self.PSSE.fact()
            self.PSSE.tysl(0)
            self.PSSE.tysl(0)
            self.PSSE.save(study_case_path.split('.')[0] + ".sav")
            self.logger.debug('Loading dynamic model....')
            ierr = self.PSSE.dyre_new([1, 1, 1, 1], dyr_path, '', '', '')
            if ierr:
                raise Exception('Error loading dynamic model file "{}"'.format(dyr_path))
            else:
                self.logger.debug('Dynamic file {} sucessfully loaded'.format(dyr_path))

            if self.export_settings["Export results using channels"]:
                self.setup_channels()

            self.PSSE.snap(sfile=snp_file)
            # Load user defined models
            for mdl in self.settings["User models"]:
                dll_path = os.path.join(self.settings["Project Path"], 'Case_study', mdl)
                self.PSSE.addmodellibrary(dll_path)
                self.logger.debug('User defined library added: {}'.format(mdl))
            # Load flow settings
            self.PSSE.fdns([0, 0, 0, 1, 1, 0, 99, 0])
        # initialize
        iErr = self.PSSE.strt_2([1, self.settings["Generators"]["Missing machine model"]], outx_path)
        if iErr:
            self.initialization_complete = False
            raise Exception('Dynamic simulation failed to successfully initialize')
        else:
            self.initialization_complete = True
            self.logger.debug('Dynamic simulation initialization sucess!')
        # get load info for the sub system
        self.load_info = self.get_load_indices(bus_subsystems)
        self.logger.debug('pyPSSE initialization complete!')
        return self.initialization_complete

    def step(self, t):
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
                    'Load ID' : load_data[0,i],
                    'Bus name' : load_data[1,i],
                    'Bus name (ext)' : load_data[2,i],
                }
            all_bus_ids[id] = load_info
        return all_bus_ids

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

    def disable_logging(self):
        self.PSSE.progress_output(islct=6,  filarg='', options=[0, 0])
        self.PSSE.prompt_output(islct=6, filarg='', options=[0, 0])
        self.PSSE.report_output(islct=6, filarg='', options=[0, 0])

    def setup_channels(self):
        import pyPSSE.Channel_map as Channel_map
        for channel, add in self.export_settings["Channels"].iteritems():
            if add:
                channelID = Channel_map.channel_map[channel]
                self.logger.debug('"{}" added to the channel file'.format(channel))
                self.PSSE.chsb(0, 1, [-1, -1, -1, 1, channelID, 0])
 
    def export(self):
        self.logger.debug('Starting export process. Can take a few minutes for large files')
        excelpath = os.path.join(self.export_path, self.settings["Excel file"])
        achnf = self.dyntools.CHNF(self.outx_path)
        achnf.xlsout(channels='', show=False, xlsfile=excelpath, outfile='', sheet='Sheet1', overwritesheet=True)
        self.logger.debug('{} export to {}'.format(self.settings["Excel file"], self.export_path))

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