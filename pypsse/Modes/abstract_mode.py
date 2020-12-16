# Standard imports
import os
from pypsse.Modes.naerm_constants import naerm_decorator

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
                    'busdt2': ['TOTAL', 'FX_TOTAL', 'SC_TOTAL', 'YS', 'YSW'], # requires string2 input
                    'busint' : ['STATION', 'TYPE', 'AREA', 'ZONE', 'OWNER', 'DUMMY'],
                    'arenam' : ['AREANAME'],
                    'stadat' : ['LATI', 'LONG'],
                    'gendat' : ['GENPOWER'],
                    'notona' : ['NAME'],
                    'busexs' : ['STATUS'],
                    'nofunc': ['NUMBER'] 
                },
                'Branches': {
                    'brndat': ['RATEn', 'RATEA', 'RATEB', 'RATEC', 'RATE', 'LENGTH', 'CHARG', 'CHARGZ', 'FRACT1', 'FRACT2',
                               'FRACT3', 'FRACT4'],
                    'brndt2': ['RX', 'ISHNT', 'JSHNT', 'RXZ', 'ISHNTZ', 'JSHNTZ', 'LOSSES', 'O_LOSSES', 'RX'],
                    'brnmsc': ['MVA', 'AMPS', 'PUCUR', 'CURANG', 'P', 'O_P', 'Q', 'O_Q', 'PLOS', 'O_PLOS', 'QLOS', 'O_QLOS'],
                    'brnint' : ['STATUS', 'METER', 'NMETR', 'OWNERS', 'OWN1', 'OWN2', 'OWN3', 'OWN4', 'STATION_I', 'STATION_J', 'SECTION_I', 'SECTION_J', 'NODE_I', 'NODE_J', 'SCTYPE'],
                    'nxtbrn' : ['FROMBUSNUM', 'TOBUSNUM', 'FROMBUSNAME', 'TOBUSNAME', 'CIRCUIT'] 
                }, 
                'Induction_generators': {
                    'inddt1': ["MBASE", "RATEKV", "PSET", "RA", "XA", "R1", "X1", "R2", "X2", "X3", "E1", "SE1", "E2",
                               "SE2", "IA1", "IA2", "XAMULT", "TRQA", "TRQB", "TRQD", "TRQE", "H", "IRATIO", "ROVERX",
                               "RZERO", "XZERO", "RGRND", "XGRND", "P", "O_P", "Q", "O_Q", "MVA", "O_MVA", "SLIP"],
                    'inddt2': ['ZA', 'Z1', 'Z2', 'ZZERO', 'ZGRND', 'PQ', 'O_PQ'],
                },
                'Loads': {
                    'loddt2': ['MVA', 'IL', 'YL', 'TOTAL', 'YNEG', 'YZERO'], # required string 2 input
                },
                'Machines': {
                    'macdat': ["QMAX", "O_QMAX", "QMIN", "O_QMIN", "PMAX", "O_PMAX", "PMIN", "O_PMIN", "MBASE", "MVA",
                               "O_MVA", "P", "O_P", "Q", "O_Q", "PERCENT", "GENTAP", "VSCHED", "WPF", "RMPCT", "RPOS",
                               "XSUBTR", "XTRANS", "XSYNCH"],
                    'macdt2': ["PQ", "O_PQ", "ZSORCE", "XTRAN", "ZPOS", "ZNEG", "ZZERO", "ZGRND"],
                    'nxtmac' : ['MACID','BUSNUM','BUSNAME'],
                    'macint' : ['STATION', 'SECTION', 'STATUS', 'IREG', 'NREG', 'OWNERS', 'WMOD', 'PERCENT', 'CZG']
                },
                'Fixed_shunts': {
                    'fxsdt2': ["ACT", "O_ACT", "NOM", "O_NOM", "PQZERO", "PQZ", "O_PQZ"]
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

    @naerm_decorator
    def read_subsystems(self, quantities, subsystem_buses, ext_string2_info={}, mapping_dict={}):

        results = {}
        for class_name, vars in quantities.items():
            if class_name in self.func_options:
                funcs = self.func_options[class_name]
                for id_, v in enumerate(vars):
                    for func_name, settinsgs in funcs.items():
                        if v in settinsgs:
                            q = "{}_{}".format(class_name, v)

                            if len(mapping_dict) !=0:
                                if class_name in mapping_dict:
                                    new_v = mapping_dict[class_name][id_]
                                    q = "{}_{}".format(class_name, new_v)
        

                            for b in subsystem_buses:
                                
                                if func_name in ['busdat', 'busdt2', 'busint','arenam', 'notona', 'busexs', 'gendat','nofunc']:

                                    if func_name == 'nofunc':
                                        if v == 'NUMBER':
                                            results =self.add_result(results, q, int(b), b)
                                    
                                    if func_name in ["busdat",  "busint"]:
                                        irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                        results =self.add_result(results, q, val, b)
                                    
                                    elif func_name == "busdt2":
                                        string2 = 'ACT'
                                        if class_name in ext_string2_info:
                                            if v in ext_string2_info[class_name]:
                                                string2 = ext_string2_info[class_name][v]

                                        irr, val = getattr(self.PSSE, func_name)(int(b), v, string2)
                                        results =self.add_result(results, q, val, b)
                                    
                                    elif func_name in ['notona', 'gendat']:
                                        irr, val = getattr(self.PSSE, func_name)(int(b))
                                        results =self.add_result(results, q, val, b)

                                    elif func_name == 'busexs':
                                        val = getattr(self.PSSE, func_name)(int(b))
                                        results =self.add_result(results, q, val, b)

                                    elif func_name == 'arenam':
                                        irr, val = self.PSSE.busint(int(b), 'AREA')
                                        if val:
                                            irr, val = getattr(self.PSSE, func_name)(val)
                                        results =self.add_result(results, q, val, b)

                                elif func_name == 'stadat':
                                   
                                    irr, val = self.PSSE.busint(int(b), 'STATION')
                                    if val:
                                        irr, val = getattr(self.PSSE, func_name)(val, v)
                                    results =self.add_result(results, q, val, b)

                                elif func_name == "loddt2":
                                    id = ''
                                    ierr = self.PSSE.inilod(int(b))
                                    while id != None:
                                        ierr, id = self.PSSE.nxtlod(int(b))
                                        irr, val = getattr(self.PSSE, func_name)(int(b), id, v, 'ACT')
                                        results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                
                                elif func_name in ["macdat", 'macdt2','nxtmac', 'macint']:
                                    ierr = self.PSSE.inimac(int(b))
                                    ierr, id = self.PSSE.nxtmac(int(b))
                                    while id != None:
                                        if func_name == 'nxtmac':
                                            if v in ['BUSNUM','MACID']:
                                                val = {'BUSNUM': int(b), 'MACID': id}[v]
                                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                            elif v == 'BUSNAME':
                                                irr, val = self.PSSE.notona(int(b))
                                                results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
                                        else:
                                            irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                            results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                        ierr, id = self.PSSE.nxtmac(int(b))
                                
                                elif func_name == 'fxsdt2':
                                    ierr = self.PSSE.inifxs(int(b))
                                    ierr, id = self.PSSE.nxtfxs(int(b))
                                    while id != None:
                                        irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                        results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                        ierr, id = self.PSSE.nxtfxs(int(b))
                                
                                elif func_name == 'swsdt1':
                                    irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                    if irr == 0: results = self.add_result(results, q, val, b)
                                
                                elif func_name in ['brndat', 'brndt2', 'brnmsc', 'brnint', 'nxtbrn']:
                                    ierr = self.PSSE.inibrx(int(b), 1)
                                    ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                    while b1 != None:
                                        if func_name == 'nxtbrn':
                                            if v in ['FROMBUSNUM', 'TOBUSNUM', 'CIRCUIT']:
                                                val = {'FROMBUSNUM' : int(b),'TOBUSNUM': int(b1),'CIRCUIT' : ickt}[v]
                                                results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
                                            elif v == 'FROMBUSNAME':
                                                irr, val = self.PSSE.notona(int(b))
                                                results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
                                            elif v == 'TOBUSNAME':
                                                irr,val = self.PSSE.notona(int(b1))
                                                results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
                                        else:
                                            irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), ickt, v)
                                            if irr == 0:
                                                results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
                                        ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                
                                elif func_name in ['xfrdat', 'tr3dt2']:
                                    ierr = self.PSSE.inibrx(int(b), 1)
                                    ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                    while b1 != None:
                                        if func_name == 'xfrdat':
                                            irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), ickt, v)
                                            if irr==0:
                                                results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
                                        ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                    ierr = self.PSSE.inibrx(int(b), 1)
                                    ierr, b1, b2, ickt = self.PSSE.nxtbrn3(int(b))
                                    while b1 != None:
                                        if func_name == 'tr3dt2':
                                            irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), int(b2), ickt, v)
                                            if irr == 0:
                                                results = self.add_result(results, q, val, "{}_{}_{}_{}".format(str(b),str(b1), str(b2), str(ickt)))
                                        ierr, b1, b2, ickt = self.PSSE.nxtbrn3(int(b))

        return results
    
    # @naerm_decorator
    # def read(self, quantities, raw_data, ext_string2_info={}, mapping_dict={}):
    #     results = {}
    #     for class_name, vars in quantities.items():
    #         if class_name in self.func_options:
    #             funcs = self.func_options[class_name]
    #             for v in vars:
    #                 for func_name, settinsgs in funcs.items():

    #                     if v in settinsgs:
    #                         q = "{}_{}".format(class_name, v)

    #                         if len(mapping_dict) !=0:
    #                             if class_name in mapping_dict:
    #                                 new_v = mapping_dict[class_name][id_]
    #                                 q = "{}_{}".format(class_name, new_v)

    #                         if func_name in ['busdat', 'busdt2', 'busint','arenam', 'notona', 'busexs', 'gendat', 'stadat']:
    #                             for b in raw_data.buses:
    #                                 if func_name == ["busdat", "busint"]:
    #                                     irr, val = getattr(self.PSSE, func_name)(int(b), v)
    #                                     results =self.add_result(results, q, val, b)
                                    
    #                                 elif func_name == "busdt2":
    #                                     string2 = 'ACT'
    #                                     if class_name in ext_string2_info:
    #                                         if v in ext_string2_info[class_name]:
    #                                             string2 = ext_string2_info[class_name][v]

    #                                     irr, val = getattr(self.PSSE, func_name)(int(b), v, string2)
    #                                     results = self.add_result(results, q, val, b)

    #                                 elif func_name in ['notona', 'gendat']:
    #                                     irr, val = getattr(self.PSSE, func_name)(int(b))
    #                                     results =self.add_result(results, q, val, b)

    #                                 elif func_name == 'busexs':
    #                                     val = getattr(self.PSSE, func_name)(int(b))
    #                                     results =self.add_result(results, q, val, b)

    #                                 elif func_name == 'arenam':
    #                                     irr, val = self.PSSE.busint(int(b), 'AREA')
    #                                     if val:
    #                                         irr, val = getattr(self.PSSE, func_name)(val)
    #                                     results =self.add_result(results, q, val, b)
                                    
    #                                 elif func_name == 'stadat':
                                   
    #                                     irr, val = self.PSSE.busint(int(b), 'STATION')
    #                                     if val:
    #                                         irr, val = getattr(self.PSSE, func_name)(val, v)
    #                                     results =self.add_result(results, q, val, b)

    #                         elif func_name == "loddt2":
    #                             for b, id in raw_data.loads:
    #                                 ierr = self.PSSE.inilod(int(b))
    #                                 irr, val = getattr(self.PSSE, func_name)(int(b), id, v, 'ACT')
    #                                 results =self.add_result(results, q, val,  '{}_{}'.format(id, b))


    #                         elif func_name in ["macdat", 'macdt2', 'nxtmac', 'macint']:
    #                             for b, id in raw_data.generators:
    #                                 ierr = self.PSSE.inimac(int(b))
    #                                 if func_name == 'nxtmac':
    #                                         if v in ['BUSNUM','MACID']:
    #                                             val = {'BUSNUM': int(b), 'MACID': id}[v]
    #                                             results = self.add_result(results, q, val, '{}_{}'.format(id, b))
    #                                         elif v == 'BUSNAME':
    #                                             irr, val = self.PSSE.notona(int(b))
    #                                             results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),str(ickt)))
    #                                 else:
    #                                     irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
    #                                     results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                            
    #                         elif func_name == 'fxsdt2':
    #                             for b, id in raw_data.fixed_stunts:
    #                                 ierr = self.PSSE.inimac(int(b))
    #                                 irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
    #                                 results = self.add_result(results, q, val, '{}_{}'.format(id, b))


    #                         elif func_name == 'swsdt1':
    #                             for b in raw_data.switched_shunt:
    #                                 irr, val = getattr(self.PSSE, func_name)(int(b), v)
    #                                 results = self.add_result(results, q, val, b)

    #                         if func_name in ['brndat', 'brndt2', 'brnmsc', 'brnint', 'nxtbrn']:
                                
    #                             for b, b1 in raw_data.branches:

    #                                 irr, val = getattr(self.PSSE, func_name)(int(b),int(b1), '1 ', v)
    #                                 results = self.add_result(results, q, val, b)


    #                         if func_name in ['xfrdat', 'tr3dt2']:
    #                             for b, b1, b2 in raw_data.transformers:
    #                                 if func_name == 'xfrdat':
    #                                     if int(b2.replace(' ', '')) == 0:
    #                                         irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), '1 ', v)
    #                                         results = self.add_result(results, q, val, b)
    #                                 elif func_name == 'xfrdat':
    #                                     if int(b2.replace(' ', '')) != 0:
    #                                         irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), int(b2), '1 ', v)
    #                                         results = self.add_result(results, q, val, b)
    #     return results

    def add_result(self, results_dict, class_name, value, label):
        if value:
            if class_name not in results_dict:
                results_dict[class_name] = {}
            results_dict[class_name][label] = value
        else:
            if class_name not in results_dict:
                results_dict[class_name] = {}
            results_dict[class_name][label] = None


        return results_dict

    def update_object(self, dType, bus, id, values):
        if dType == "Load":
            ierr = self.PSSE.load_chng_5(ibus=int(bus), id=id, **values)
        elif dType == "Induction_machine":
            ierr = self.PSSE.induction_machine_data(ibus=int(bus), id=id, **values)
        elif dType == "Machine":
            ierr = self.PSSE.machine_data_2(i=int(bus), id=id, **values)
        elif dType == "Plant":
            ierr = self.PSSE.plant_data_4(ibus=int(bus), inode=id, **values)
        else:
            ierr = 1

        if ierr == 0:
            self.logger.info(f"Profile Manager: {dType} '{id}' on bus '{bus}' has been updated. {values}")
        else:
            self.logger.error(f"Profile Manager: Error updating {dType} '{id}' on bus '{bus}'.")