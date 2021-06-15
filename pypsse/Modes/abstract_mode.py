# Standard imports
import os
from pypsse.Modes.naerm_constants import naerm_decorator
import numpy as np

class AbstractMode:

    def __init__(self, psse, dyntools, settings, export_settings, logger, subsystem_buses):
        self.PSSE = psse

        self.bus_freq_channels = {}

        from psspy import _i,_f,_s,_o
        self._i = _i
        self._f = _f
        self._s = _s
        self._o = _o

        self.sub_buses = subsystem_buses
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
                    'busnofunc': ['NUMBER', 'ISLOADBUS'],
                    'frequency': ["FREQ"]
                },
                "Stations": {
                    "stanofunc": ["SUBNAME", "SUBNUMBER", "BUSES", "GENERATORS","TRANSFORMERS", "NOMKV", "LOADMW", "GENMW" ]
                },
                "Areas" : {
                    "arenofunc" : ["AREANAME", "AREANUMBER"],
                    "ardat" : ["LOAD", "LOADLD", "LDGN", "LDGNLD", "GEN"]
                },
                "Zones" : {
                    "zonnofunc" : ["ZONENAME", "ZONENUMBER"],
                    "zndat": ["LOAD", "LOADID", "LDGN", "LDGNLD", "GEN", "LOSS"]
                },
                "DCtransmissionlines": {
                    'dctnofunc' : ['DCLINENAME'],
                    'dc2int_2' : ['MDC', 'RECT', 'INV', 'METER', 'NBR', 'NBI', 'ICR', 'ICI', 'NDR', 'NDI']
                },
                'Branches': {
                    'brndat': ['RATEn', 'RATEA', 'RATEB', 'RATEC', 'RATE', 'LENGTH', 'CHARG', 'CHARGZ', 'FRACT1', 'FRACT2',
                               'FRACT3', 'FRACT4'],
                    'brndt2': ['RX', 'ISHNT', 'JSHNT', 'RXZ', 'ISHNTZ', 'JSHNTZ', 'LOSSES', 'O_LOSSES', 'RX'],
                    'brnmsc': ['MVA', 'AMPS', 'PUCUR', 'CURANG', 'P', 'O_P', 'Q', 'O_Q', 'PLOS', 'O_PLOS', 'QLOS', 'O_QLOS', 'PCTRTA'],
                    'brnint' : ['STATUS', 'METER', 'NMETR', 'OWNERS', 'OWN1', 'OWN2', 'OWN3', 'OWN4', 'STATION_I', 'STATION_J', 'SECTION_I', 'SECTION_J', 'NODE_I', 'NODE_J', 'SCTYPE'],
                    'brnnofunc' : ['FROMBUSNUM', 'TOBUSNUM', 'FROMBUSNAME', 'TOBUSNAME', 'CIRCUIT', 'SUBNUMBERTO', 'SUBNUMBERFROM', 'FROMAREANUMBER', 'TOAREANUMBER'] 
                }, 
                'Induction_generators': {
                    'inddt1': ["MBASE", "RATEKV", "PSET", "RA", "XA", "R1", "X1", "R2", "X2", "X3", "E1", "SE1", "E2",
                               "SE2", "IA1", "IA2", "XAMULT", "TRQA", "TRQB", "TRQD", "TRQE", "H", "IRATIO", "ROVERX",
                               "RZERO", "XZERO", "RGRND", "XGRND", "P", "O_P", "Q", "O_Q", "MVA", "O_MVA", "SLIP"],
                    'inddt2': ['ZA', 'Z1', 'Z2', 'ZZERO', 'ZGRND', 'PQ', 'O_PQ'],
                    'indnofunc': ["INDID", "BUSNUM", "BUSNAME"]
                },
                'Loads': {
                    'loddt2': ["MVA", "IL", "YL", "TOTAL", "YNEG", "YZERO"], # required string 2 input
                    'lodnofunc': ["LOADID", "BUSNUM", "BUSNAME"],
                    'lodint': ['STATION', 'SECTION', 'STATUS', 'AREA', 'ZONE', 'OWNER', 'SCALE', 'CGR']
                },
                'Machines': {
                    'macdat': ["QMAX", "O_QMAX", "QMIN", "O_QMIN", "PMAX", "O_PMAX", "PMIN", "O_PMIN", "MBASE", "MVA",
                               "O_MVA", "P", "O_P", "Q", "O_Q", "PERCENT", "GENTAP", "VSCHED", "WPF", "RMPCT", "RPOS",
                               "XSUBTR", "XTRANS", "XSYNCH"],
                    'macdt2': ["PQ", "O_PQ", "ZSORCE", "XTRAN", "ZPOS", "ZNEG", "ZZERO", "ZGRND"],
                    'macnofunc' : ['MACID','BUSNUM','BUSNAME', 'SUBNUMBER', 'SUBLATITUDE', 'SUBLONGITUDE','AREANUMBER'],
                    'macint' : ['STATION', 'SECTION', 'STATUS', 'IREG', 'NREG', 'OWNERS', 'WMOD', 'PERCENT', 'CZG']
                },
                'Fixed_shunts': {
                    'fxsdt2': ["ACT", "O_ACT", "NOM", "O_NOM", "PQZERO", "PQZ", "O_PQZ"],
                    'fxsnofunc' : ["FXSHID", "BUSNUM", "BUSNAME"]
                },
                'Switched_shunts': {
                    'swsdt1': ["VSWHI", "VSWLO", "RMPCT", "BINIT", "O_BINIT"],
                    "swsnofunc": ["BUSNUM", "BUSNAME"]
                },
                'Transformers': {
                    'xfrdat': ['RATIO', 'RATIO2', 'ANGLE', 'RMAX', 'RMIN', 'VMAX', 'VMIN', 'STEP', 'CR', 'CX', 'CNXANG',
                                'SBASE1', 'NOMV1', 'NOMV2', 'NOMV2', 'GMAGNT', 'BMAGNT', 'RG1', 'XG1', 'R01', 'X01', 'RG2',
                                'XG2', 'R02', 'X02', 'RNUTRL', 'XNUTRL'],
                    'tr3dt2': ['RX1-2', 'RX2-3', 'RX3-1', 'YMAGNT', 'ZG1', 'Z01', 'ZG2', 'Z02', 'ZG3', 'Z03', 'ZNUTRL' ],
                    'trfnofunc': ['FROMBUSNUM_3WDG','FROMBUSNUM_2WDG','TOBUSNUM_3WDG','TOBUSNUM_2WDG', 'TOBUS2NUM_3WDG', \
                        'FROMBUSNAME_3WDG','FROMBUSNAME_2WDG','TOBUSNAME_3WDG','TOBUSNAME_2WDG', 'TOBUS2NAME_3WDG','CIRCUIT_2WDG', 'CIRCUIT_3WDG']
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

    
    def get_area_numbers(self, subsystem_buses):
        area_numbers = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'AREA')
            if val:
                area_numbers.append(val)
        return list(set(area_numbers))

    def get_substation_numbers(self, subsystem_buses):
        substation_numbers = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val:
                substation_numbers.append(val)
        return list(set(substation_numbers))


    def get_zone_numbers(self, subsystem_buses):
        zone_numbers = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'ZONE')
            if val:
                zone_numbers.append(val)
        return list(set(zone_numbers))

    def get_dctr_line_names(self, subsystem_buses):
        dc_lines = []
        ierr = self.PSSE.ini2dc()
        ierr, dc_line_name = self.PSSE.nxtmdc()
        while dc_line_name != None:
            ierr, rectbus = dc2int_2(dc_line_name, 'RECT')
            ierr, invbus = dc2int_2(dc_line_name, 'INV')
            if rectbus in subsystem_buses and invbus in subsystem_buses:
                dc_lines.append(dc_line_name)

            ierr, dc_line_name = self.PSSE.nxt2dc()
        return list(set(dc_lines))

    def get_a_list_of_buses_in_substation(self, sub_number, subsystem_buses):
        bus_numbers = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val==sub_number:
                bus_numbers.append(int(b))
        return list(set(bus_numbers))

    def get_a_list_of_nomkv_in_substation(self, sub_number, subsystem_buses):
        
        nom_kvs = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val==sub_number:
                irr, val = self.PSSE.busdat(int(b), "KV")
                nom_kvs.append(val)
        return list(set(nom_kvs))

    def get_a_loadmw_in_substation(self, sub_number, subsystem_buses):
        
        load_mw = 0
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val==sub_number:
                ierr = self.PSSE.inilod(int(b))
                ierr, id = self.PSSE.nxtlod(int(b))
                while ierr ==0:
                    irr, val = self.PSSE.loddt2(int(b), id, 'TOTAL', 'ACT')
                    if isinstance(val, complex):
                        load_mw += val.real
                    ierr, id = self.PSSE.nxtlod(int(b))
        return load_mw

    def get_a_genmw_in_substation(self, sub_number, subsystem_buses):
        
        gen_mw = 0
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val==sub_number:
                ierr, val = self.PSSE.gendat(int(b))
                if isinstance(val, complex):
                    gen_mw += val.real
        return gen_mw

    def get_a_list_of_generators_in_substation(self,sub_number, subsystem_buses):
        generators = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val==sub_number:
                ierr = self.PSSE.inimac(int(b))
                ierr, id = self.PSSE.nxtmac(int(b))
                while ierr==0:
                    gen_name = f'{b}_{id}'
                    ierr, id = self.PSSE.nxtmac(int(b))
                    generators.append(gen_name)

        return list(set(generators))

    def get_a_list_of_transformers_in_substation(self,sub_number, subsystem_buses):
        
        transformers = []
        for b in subsystem_buses:
            irr, val = self.PSSE.busint(int(b), 'STATION')
            if val==sub_number:
                
                # Get two winding transformers
                ierr = self.PSSE.inibrx(int(b), 1)
                ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                ickt_string = str(ickt)
                while ierr == 0:
                    irr, val = self.PSSE.xfrdat(int(b), int(b1), ickt, 'RATIO')
                    if irr ==0:
                        t_name = f'{b}_{b1}_{ickt_string}'
                        transformers.append(t_name)
                    ierr, b1, ickt = self.PSSE.nxtbrn(int(b))

                # Get three winding transformers
                ierr = self.PSSE.inibrx(int(b), 1)
                ierr, b1, b2, ickt = self.PSSE.nxtbrn3(int(b))
                ickt_string = str(ickt)
                while ierr ==0:                
                    irr, val = self.PSSE.tr3dt2(int(b), int(b1), int(b2), ickt, 'Z01')
                    if irr == 0:
                        t_name = "{}_{}_{}_{}".format(str(b),str(b1), str(b2), ickt_string)
                        transformers.append(t_name)
                    ierr, b1, b2, ickt = self.PSSE.nxtbrn3(int(b))

        return list(set(transformers))

    def check_for_loadbus(self,b):

        ierr = self.PSSE.inilod(int(b))
        if ierr == 0:
            ierr = self.PSSE.inimac(int(b))
            if ierr ==2:
                return 1
        
        return 0

    @naerm_decorator
    def read_subsystems(self, quantities, subsystem_buses, ext_string2_info={}, mapping_dict={}):
        print("here")
        results = {}
        area_numbers = self.get_area_numbers(subsystem_buses)
        zone_numbers = self.get_zone_numbers(subsystem_buses)
        dctr_lines = self.get_dctr_line_names(subsystem_buses)
        substation_numbers = self.get_substation_numbers(subsystem_buses)

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
        
                            if class_name == 'Areas':
                                for arr_num in area_numbers:
                                    if func_name in ['arenofunc']:
                                        if v == 'AREANUMBER':
                                            results =self.add_result(results, q, int(arr_num), arr_num)
                                        elif v == 'AREANAME':
                                            irr, val = getattr(self.PSSE, 'arenam')(int(arr_num))
                                            results =self.add_result(results, q, val, arr_num)
                            
                            elif class_name == 'Stations':
                                for sub_num in substation_numbers:
                                    if func_name in ['stanofunc']:
                                        if v == 'SUBNUMBER':
                                            results =self.add_result(results, q, int(sub_num), sub_num)
                                        elif v == 'SUBNAME':
                                            irr, val = getattr(self.PSSE, 'staname')(int(sub_num))
                                            results =self.add_result(results, q, val, sub_num)
                                        elif v== 'BUSES':
                                            val = self.get_a_list_of_buses_in_substation(sub_num, subsystem_buses)
                                            results =self.add_result(results, q, val, sub_num)
                                        elif v=='GENERATORS':
                                            val = self.get_a_list_of_generators_in_substation(sub_num, subsystem_buses)
                                            results =self.add_result(results, q, val, sub_num)
                                        elif v=='TRANSFORMERS':
                                            val = self.get_a_list_of_transformers_in_substation(sub_num, subsystem_buses)
                                            results =self.add_result(results, q, val, sub_num)
                                        elif v=='NOMKV':
                                            val = self.get_a_list_of_nomkv_in_substation(sub_num, subsystem_buses)
                                            results =self.add_result(results, q, max(val), sub_num)
                                        elif v=='LOADMW':
                                            val = self.get_a_loadmw_in_substation(sub_num, subsystem_buses)
                                            results =self.add_result(results, q, val, sub_num)
                                        elif v=='GENMW':
                                            val = self.get_a_genmw_in_substation(sub_num, subsystem_buses)
                                            results =self.add_result(results, q, val, sub_num)

                            elif class_name == 'Zones':
                                for zn_num in zone_numbers:
                                    if func_name in ['zonnofunc']:
                                        if v == 'ZONENUMBER':
                                            results =self.add_result(results, q, int(zn_num), zn_num)
                                        elif v == 'ZONENAME':
                                            irr, val = getattr(self.PSSE, 'zonnam')(int(zn_num))
                                            results =self.add_result(results, q, val, zn_num)

                            elif class_name == 'DCtransmissionlines':
                                for dcline in dctr_lines:
                                    if func_name == 'dctnofunc':
                                        if v == 'DCLINENAME':
                                            results =self.add_result(results, q, dcline, dcline)
                                    elif func_name == 'dc2int_2':
                                        ierr, val = getattr(self.PSSE, func_name)(dcline, v)
                                        results =self.add_result(results, q, val, dcline)

                            else:
                                for b in subsystem_buses:
                                    
                                    if func_name in ['busdat', 'busdt2', 'busint','arenam', 'notona', 'busexs', 'gendat','busnofunc', 'frequency']:

                                        if func_name == 'busnofunc':
                                            if v == 'NUMBER':
                                                results =self.add_result(results, q, int(b), b)
                                            if v == 'ISLOADBUS':
                                                val = self.check_for_loadbus(b)
                                                results =self.add_result(results, q, val, b)

                                        if func_name == 'frequency':
                                            if v == 'FREQ':
                                                if b in self.bus_freq_channels:
                                                    irr, val = self.PSSE.chnval(self.bus_freq_channels[b])
                                                    if not val:
                                                        val = np.nan
                                                    results =self.add_result(results, q, val, int(b))
                                                else:
                                                    results = self.add_result(results, q, 0, int(b))

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
                                            val = not val #PSSE is weird, 0 means bus exist so had to negate
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

                                    elif func_name in ["inddt1", "inddt2", "indnofunc"]:
                                        ierr = self.PSSE.iniind(int(b))
                                        ierr, id = self.PSSE.nxtind(int(b))
                                        while id != None:
                                            if func_name == "indnofunc":
                                                if v in ['BUSNUM', 'INDID']:
                                                    val = {'INDID': id, 'BUSNUM': int(b)}[v]
                                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                                elif v == 'BUSNAME':
                                                    irr, val = self.PSSE.notona(int(b))
                                                    results = self.add_result(results, q, val, "{}_{}".format(id,b))
                                            else:    
                                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                            ierr, id = self.PSSE.nxtind(int(b))

                                    elif func_name in ["loddt2", "lodnofunc", "lodint"]:
                                        ierr = self.PSSE.inilod(int(b))
                                        ierr, id = self.PSSE.nxtlod(int(b))
                                        while id != None:
                                            if func_name == "lodnofunc":
                                                if v in ['BUSNUM', 'LOADID']:
                                                    val = {'LOADID': id, 'BUSNUM': int(b)}[v]
                                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                                elif v == 'BUSNAME':
                                                    irr, val = self.PSSE.notona(int(b))
                                                    results = self.add_result(results, q, val, "{}_{}".format(id, b))
                                            elif func_name == "loddt2":    
                                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v, 'ACT')
                                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                            elif func_name == "lodint":
                                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))

                                            ierr, id = self.PSSE.nxtlod(int(b))
                                    
                                    elif func_name in ["macdat", 'macdt2','macnofunc', 'macint']:
                                
                                        ierr = self.PSSE.inimac(int(b))
                                        ierr, id = self.PSSE.nxtmac(int(b))
                                        while id != None:
                                            if func_name == 'macnofunc':
                                                if v in ['BUSNUM','MACID']:
                                                    val = {'BUSNUM': int(b), 'MACID': id}[v]
                                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                                elif v == 'BUSNAME':
                                                    irr, val = self.PSSE.notona(int(b))
                                                    results = self.add_result(results, q, val, "{}_{}".format(id,b))
                                                elif v == 'SUBNUMBER':
                                                    irr, val = self.PSSE.busint(int(b), 'STATION')
                                                    results = self.add_result(results, q, val, "{}_{}".format(id,b))

                                                elif v == "AREANUMBER":
                                                    irr, val = self.PSSE.busint(int(b), 'AREA')
                                                    results = self.add_result(results, q, val, "{}_{}".format(id,b))

                                                elif v in ['SUBLATITUDE', 'SUBLONGITUDE']:
                                                    sub_dict = {'SUBLATITUDE': 'LATI', 'SUBLONGITUDE': 'LONG'}
                                                    irr, val = self.PSSE.busint(int(b), 'STATION')
                                                    if val:
                                                        irr, val = getattr(self.PSSE, 'stadat')(val, sub_dict[v])
                                                    results =self.add_result(results, q, val, b)
                                            else:
                                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                            ierr, id = self.PSSE.nxtmac(int(b))
                                    
                                    elif func_name in ['fxsdt2','fxsnofunc']:
                                        ierr = self.PSSE.inifxs(int(b))
                                        ierr, id = self.PSSE.nxtfxs(int(b))
                                        while id != None:
                                            if func_name == 'fxsnofunc':
                                                if v in ['BUSNUM','FXSHID']:
                                                    val = {'BUSNUM': int(b), 'FXSHID': id}[v]
                                                    results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                                elif v == 'BUSNAME':
                                                    irr, val = self.PSSE.notona(int(b))
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(id,b))
                                            else:
                                                irr, val = getattr(self.PSSE, func_name)(int(b), id, v)
                                                results = self.add_result(results, q, val, '{}_{}'.format(id, b))
                                            ierr, id = self.PSSE.nxtfxs(int(b))
                                    
                                    elif func_name in ['swsdt1','swsnofunc']:
                                        if func_name == 'swsnofunc': 
                                            irr, val = getattr(self.PSSE, 'swsint')(int(b), 'STATUS')
                                        else:
                                            irr, val = getattr(self.PSSE, func_name)(int(b), v)
                                        if irr == 0: 
                                            if func_name == 'nofunc':
                                                if v == 'BUSNUM':
                                                    val = int(b)
                                                elif v == 'BUSNAME':
                                                    irr, val = self.PSSE.notona(int(b))
                                            results = self.add_result(results, q, val, b)
                                    
                                    elif func_name in ['brndat', 'brndt2', 'brnmsc', 'brnint', 'brnnofunc']:
                                        ierr = self.PSSE.inibrx(int(b), 1)
                                        ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                        ickt_string = str(ickt)
                                        while ierr==0:
                                            if func_name == 'brnnofunc':
                                                if v in ['FROMBUSNUM', 'TOBUSNUM', 'CIRCUIT']:
                                                    val = {'FROMBUSNUM' : int(b),'TOBUSNUM': int(b1),'CIRCUIT' : ickt_string}[v]
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                elif v == 'FROMBUSNAME':
                                                    irr, val = self.PSSE.notona(int(b))
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                elif v == 'TOBUSNAME':
                                                    irr,val = self.PSSE.notona(int(b1))
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                elif v in ['SUBNUMBERTO', 'SUBNUMBERFROM']:
                                                    sub_dict = {'SUBNUMBERFROM': int(b), 'SUBNUMBERTO': int(b1)}
                                                    ierr, val = self.PSSE.busint(sub_dict[v], 'STATION')
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                            
                                                elif v in ['FROMAREANUMBER', 'TOAREANUMBER']:
                                                    bus_dict = {'FROMAREANUMBER': int(b), 'TOAREANUMBER': int(b1)}
                                                    irr, val = self.PSSE.busint(bus_dict[v], 'AREA')
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))

                                            else:
                                                irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), str(ickt), v)
                                                if irr == 0:
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                            ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                    
                                    elif func_name in ['xfrdat', 'tr3dt2', 'trfnofunc']:
                                        ierr = self.PSSE.inibrx(int(b), 1)
                                        ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                        ickt_string = str(ickt)
                                        while ierr == 0:
                                            if func_name == 'xfrdat':
                                                irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), ickt, v)
                                                if irr==0:
                                                    results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                            elif func_name == 'trfnofunc':
                                                if v.split('_')[1] == '2WDG':
                                                    if v in ['FROMBUSNUM_2WDG', 'TOBUSNUM_2WDG', 'CIRCUIT_2WDG']:
                                                        val = {'FROMBUSNUM_2WDG' : int(b),'TOBUSNUM_2WDG': int(b1),'CIRCUIT_2WDG' : ickt}[v]
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                    elif v == 'FROMBUSNAME_2WDG':
                                                        irr, val = self.PSSE.notona(int(b))
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                    elif v == 'TOBUSNAME_2WDG':
                                                        irr,val = self.PSSE.notona(int(b1))
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))

                                            ierr, b1, ickt = self.PSSE.nxtbrn(int(b))
                                        
                                        ierr = self.PSSE.inibrx(int(b), 1)
                                        ierr, b1, b2, ickt = self.PSSE.nxtbrn3(int(b))
                                        ickt_string = str(ickt)
                                        while ierr ==0:
                                            if func_name == 'tr3dt2':
                                                irr, val = getattr(self.PSSE, func_name)(int(b), int(b1), int(b2), ickt, v)
                                                if irr == 0:
                                                    results = self.add_result(results, q, val, "{}_{}_{}_{}".format(str(b),str(b1), str(b2), ickt_string))
                                            elif func_name == 'trfnofunc':
                                                if v.split('_')[1] == '3WDG':
                                                    if v in ['FROMBUSNUM_3WDG', 'TOBUSNUM_3WDG', 'TOBUS2NUM_3WDG', 'CIRCUIT_3WDG']:
                                                        val = {'FROMBUSNUM_3WDG' : int(b),'TOBUSNUM_3WDG': int(b1),'CIRCUIT_3WDG' : ickt, 'TOBUS2NUM_3WDG': int(b2)}[v]
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                    elif v == 'FROMBUSNAME_3WDG':
                                                        irr, val = self.PSSE.notona(int(b))
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                    elif v == 'TOBUSNAME_3WDG':
                                                        irr,val = self.PSSE.notona(int(b1))
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
                                                    elif v == 'TOBUS2NAME_3WDG':
                                                        irr,val = self.PSSE.notona(int(b1))
                                                        results = self.add_result(results, q, val, "{}_{}_{}".format(str(b),str(b1),ickt_string))
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
        if value or value==0:
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