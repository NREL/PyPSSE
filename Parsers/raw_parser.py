import logging
import os
import re

class raw_parser:
    valid_verions = ['3']
    def __init__(self, settings , logger=None):
        if logger != None:
            self.logger = logger
        else:
            formatter = logging.Formatter('%(message)s')
            logging.getLogger('').setLevel(logging.DEBUG)
            fh = logging.FileHandler('a.log')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logging.getLogger('').addHandler(fh)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            logging.getLogger('').addHandler(ch)
            self.logger = logging
            self.logger.debug('Starting RAW parser')

        self.settings = settings

        self.filepath = os.path.join(settings["Project Path"], "Case_study", settings["Raw file"])


        self.buses = self.get_all_buses('BUS')
        self.loads = self.get_element_data('LOAD')
        self.fixed_stunts = self.get_element_data('FIXED SHUNT')
        self.generators = self.get_element_data('GENERATOR')
        self.branches = self.get_branch_data('BRANCH')
        self.transformers = self.get_transformer_data()
        self.Area = self.get_all_buses('AREA')
        self.DC_branch = self.get_branch_data('TWO-TERMINAL DC')
        #self.voltage_source = self.get_all_buses('VOLTAGE SOURCE CONVERTER')
        self.impedance_correction = self.get_all_buses('IMPEDANCE CORRECTION')
        self.multi_term_dc = self.get_element_data('MULTI-TERMINAL DC')
        self.multi_line = self.get_branch_data('MULTI-SECTION LINE')
        self.zones = self.get_element_data('ZONE')
        self.inter_area_transfer = self.get_all_buses('INTER-AREA TRANSFER')
        self.owners = self.get_element_data('OWNER')
        #self.facts = self.get_element_data('FACTS CONTROL DEVICE')
        self.switched_shunt = self.get_all_buses('SWITCHED SHUNT')
        #self.gne_device = self.get_element_data('GNE DEVICE')
        return

    def get_transformer_data(self):
        self.logger.info("Parsing transformers")
        filehandle = open(self.filepath, 'r')
        line = ''
        while 'BEGIN {} DATA'.format('TRANSFORMER') not in line:
            line = filehandle.readline()

        element = []
        while True:
            line = filehandle.readline()
            while line.startswith('@'):
                line = filehandle.readline()


            if 'END OF TRANSFORMER DATA' in line:
                break
            data = line.split(',')
            bus_id_1 = data[0]
            bus_id_2 = data[1]
            bus_id_3 = data[2]
            element.append([bus_id_1, bus_id_2, bus_id_3])
            if bus_id_3 == "0" or bus_id_3 == "    0" or bus_id_3 == '     0':
                Dummy = [filehandle.readline() for i in range(3)]
            else:
                Dummy = [filehandle.readline() for i in range(4)]
        filehandle.close()
        return element

    def get_branch_data(self, elm):
        self.logger.info("Parsing {}".format(elm.lower()))
        filehandle = open(self.filepath, 'r')
        line = ''
        while 'BEGIN {} DATA'.format(elm) not in line:
            line = filehandle.readline()

        element = []
        while True:
            line = filehandle.readline()
            if 'END OF {} DATA'.format(elm) in line:
                break
            data = line.split(',')
            bus_id = data[0]
            elm_id = data[1]
            element.append([bus_id, elm_id])
        filehandle.close()
        self.logger.info("{} count: {}".format(elm, len(element)))
        return element

    def get_all_buses(self, elm):
        self.logger.info("Parsing {}".format(elm.lower()))
        filehandle = open(self.filepath, 'r')
        line = ''
        while 'BEGIN {} DATA'.format(elm) not in line:
            line = filehandle.readline()
        buses = []
        while True:
            line = filehandle.readline()
            while line.startswith('@'):
                line = filehandle.readline()
            if 'END OF {} DATA'.format(elm) in line:
                break
            bus_id = line.split(',')[0]
            buses.append(bus_id)

        filehandle.close()
        self.logger.info("{} count: {}".format(elm, len(buses)))
        return buses

    def get_element_data(self, elm):
        self.logger.info("Parsing {}".format(elm.lower()))
        filehandle = open(self.filepath, 'r')

        line = ''
        while 'BEGIN {} DATA'.format(elm) not in line:
            line = filehandle.readline()

        element = []
        while True:
            line = filehandle.readline()
            while line.startswith('@'):
                line = filehandle.readline()
            if 'END OF {} DATA'.format(elm) in line:
                break
            data = line.split(',')
            bus_id = data[0]
            elm_id = re.findall(r"'(.*?)'", data[1])[0]
            element.append([bus_id, elm_id])
        filehandle.close()
        self.logger.info("{} count: {}".format(elm, len(element)))
        return element

#
# settings =  {
#     "Project Path" : r"C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model",
#     "Raw file" : "ACTIVSg10k.RAW",
#
# }
# a = raw_parser(settings)

