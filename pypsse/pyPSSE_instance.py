# -*- coding:utf-8 -*-
"""
@author:Aadil Latif
@file:pyPSSE.py
@time:2/4/2020
"""

#
# import csv
# import win32api
#
# import time

from pypsse.helics_interface import helics_interface
import pypsse.simulation_controller as sc
import pypsse.pyPSSE_logger as Logger
from pypsse.Parsers import gic_parser as gp
from pypsse.Parsers import reader as rd
import pypsse.contingencies as c
import subprocess
import pandas as pd
import numpy as np
import os, sys
import toml
from pypsse.result_container import container
class pyPSSE_instance:

    def __init__(self, settinigs_toml_path, options=None):
        self.initComplete = False
        self.hi = None

        nBus = 200000
        self.settings = self.read_settings(settinigs_toml_path)
        export_settings_path = os.path.join(self.settings["Project Path"], 'Settings', 'export_settings.toml')
        self.export_settings = self.read_settings(export_settings_path)

        log_path = os.path.join(self.settings["Project Path"], 'Logs')
        self.logger = Logger.getLogger('pyPSSE', log_path, LoggerOptions=self.settings)
        self.logger.debug('Starting PSSE instance')
        sys.path.append(self.settings["PSSE_path"])
        os.environ['PATH'] += ';' + self.settings["PSSE_path"]

        #** Initialize PSSE modules
        import psse34
        import psspy
        import dyntools



        self.dyntools = dyntools
        self.PSSE = psspy
        self.PSSE.psseinit(nBus)

        self.initComplete = True

        self.PSSE.case(os.path.join(self.settings["Project Path"], "Case_study", self.settings["Case study"]))
        self.raw_data = rd.Reader(self.PSSE, self.settings, self.logger)

        self.sim = sc.sim_controller(self.PSSE, self.dyntools, self.settings, self.export_settings, self.logger)
        self.bus_subsystems, self.all_subsysten_buses = self.define_bus_subsystems()

        self.contingencies = self.build_contingencies()

        bokeh_server_proc = None

        if self.settings["Cosimulation mode"]:
            self.hi = helics_interface(self.PSSE, self.settings, self.logger)
            self.hi.create_federate()
            self.publications = self.hi.register_publications(self.bus_subsystems)
            if self.settings["Create subscriptions"]:
                self.subscriptions = self.hi.register_subscriptions(self.bus_subsystems)


        if len(self.settings["GIC file"]):
            self.network_graph = self.parse_GIC_file()
            self.bus_ids = self.network_graph.nodes.keys()
        else:
            self.network_graph = None


        self.results = container(self.settings, self.export_settings)
        self.exp_vars = self.results.get_export_variables()

        self.initComplete = True
        return


    def initialize_loads(self):
        #         data = pd.read_csv(r'C:\NAERM-global\init_Conditions_3_new.csv', header=0, index_col=None)
        # data = data.values
        # r, c = data.shape
        # for i in range(r):
        #     bus_data = data[i, :]
        #     bus_id = bus_data[0]
        #     P = bus_data[3]
        #     Q = bus_data[4]
        #
        #     ierr = self.PSSE.load_chng_5(ibus=int(bus_id), id='1', realar=[P, Q, 0, 0, 0, 0, 0, 0])
        #     if ierr:
        #         self.logger.debug('ERROR: Load not updated')
        return

    def init(self):
        sucess = self.sim.init(self.bus_subsystems)
        if sucess:
            self.load_info = self.sim.load_info
        else:
            self.load_info = None

        if self.settings["Cosimulation mode"]:
            self.hi.enter_execution_mode()
        return

    def parse_GIC_file(self):
        gicdata = gp.gic_parser(self.settings, self.logger)
        return gicdata.psse_graph

    def define_bus_subsystems(self):
        bus_subsystems_dict = {}
        bus_subsystems = self.get_bus_indices()
        # valid bus subsystem ID. Valid bus subsystem IDs range from 0 to 11 (PSSE documentation)
        if len(bus_subsystems) > 12:
            raise Exception("Number of subsystems can not be more that 12. See PSSE documentation")

        all_subsysten_buses = []
        for i , buses in enumerate(bus_subsystems):
            all_subsysten_buses.extend(buses)
            ierr = self.PSSE.bsysinit(i)
            if ierr:
                raise Exception("Failed to create bus subsystem for FIVR event buses.")
            else:
                self.logger.debug('Bus subsystem "{}" created'.format(i))

            ierr = self.PSSE.bsys(sid=i, numbus=len(buses), buses=buses)
            if ierr:
                raise Exception ("Failed to add buses to bus subsystem.")
            else:
                bus_subsystems_dict[i] = buses
                self.logger.debug('Buses {} added to subsystem "{}"'.format(buses, i))
        all_subsysten_buses = [str(x) for x in all_subsysten_buses]
        return bus_subsystems_dict, all_subsysten_buses


    def get_bus_indices(self):
        if self.settings['bus_subsystems']["from_file"]:
            bus_file = os.path.join(self.settings["Project Path"], 'Case_study',
                                    self.settings['bus_subsystems']["bus_file"])
            bus_info = pd.read_csv(bus_file, index_col=None)
            bus_info = bus_info.values
            r, c =  bus_info.shape
            bus_data = []
            for col in range(c):
                data = [int(x) for x in bus_info[:,col] if not np.isnan(x)]
                bus_data.append(data)
        else:
            bus_data = self.settings['bus_subsystems']["bus_subsystem_list"]
        return bus_data

    def read_settings(self, settinigs_toml_path):
        settings_text = ''
        f = open(settinigs_toml_path, "r")
        text = settings_text.join(f.readlines())
        toml_data = toml.loads(text)
        toml_data = {str(k): (str(v) if isinstance(v, str) else v) for k, v in toml_data.items()}
        f.close()
        return toml_data

    def run(self):


        if self.sim.initialization_complete:
            if self.settings['Plotting']["Enable dynamic plots"]:
                bokeh_server_proc = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
            else:
                bokeh_server_proc = None
            self.initialize_loads()
            self.logger.debug('Running dynamic simulation for time (sec), {}'.format(self.settings["Simulation time (sec)"]))
            self.logger.debug('Simulation time step (sec), {}'.format(self.settings["Step resolution (sec)"]))
            T = self.settings["Simulation time (sec)"]
            t = 0
            self.test = False
            while True:
                dT = self.check_contingency_updates(t)
                if dT:
                    T += dT

                self.step(t)


                t += self.settings["Step resolution (sec)"]
                if t >= T:
                    break

            self.PSSE.pssehalt_2()

            if not self.export_settings["Export results using channels"]:
                self.results.export_results()
            else:
                self.sim.export()

            if bokeh_server_proc != None:
                bokeh_server_proc.terminate()
        else:
            self.logger.error(
                'Run init() command to initialize models before running the simulation')
        return

    def check_contingency_updates(self, t):
        if t > 1 and not self.test:
            self.test = True
            return 0.1
        return

    def get_bus_ids(self):
        ierr, iarray = self.PSSE.abusint(-1, 1, 'NUMBER')
        return iarray

    def step(self, t):
        self.update_contingencies(t)
        self.logger.debug('Simulation time: {} seconds'.format(t))
        self.sim.step(t)
        if self.settings["Cosimulation mode"]:
            self.publish_bus_voltages(t, bus_subsystem_id = 0)
            self.logger.debug('Time requested: {}'.format(t))
            helics_time = self.update_federate_time(t)
            self.logger.debug('Time granted: {}'.format(helics_time))
            if self.settings["Create subscriptions"]:
                self.update_subscriptions(t)
        if self.export_settings['Defined bus subsystems only']:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.all_subsysten_buses)
        else:
            curr_results = self.sim.read(self.exp_vars, self.raw_data)
        if not self.export_settings["Export results using channels"]:
            self.results.Update(curr_results, None, t, self.sim.getTime())
        return curr_results

    def update_subscriptions(self, t):
        data = self.hi.subscribe()
        values = {}
        for sub_id, info in data.items():
            bus_subsystem_id = int(info['bus_subsystem_id'])
            if bus_subsystem_id in self.load_info:
                bus_id = int(info['bus_id'])
                if bus_id in self.load_info[bus_subsystem_id]:
                    load_id = str(info['load_id'])
                    new_load_id = self.load_info[bus_subsystem_id][bus_id]['Load ID']
                    if load_id == new_load_id[:-1]:
                        val_id = '{}.{}.{}'.format(bus_subsystem_id, bus_id, new_load_id)
                        if val_id not in values:
                            values[val_id] = {}
                        values[val_id][info['load_type']] = info['value'] * info['scaler']
                    else:
                        self.logger.debug('Not valid load id.')
                else:
                    self.logger.debug('Not valid bus id.')
            else:
                self.logger.debug('Not valid bus sub system id.')

        for key, info in values.items():
            bus_sub, bus_id, load_id = [x for x in key.split('.')]
            if info['P'] != 0:
                ierr = self.PSSE.load_chng_5(ibus=int(bus_id), id=load_id,
                                             realar=[abs(info['P']), abs(info['Q']), 0, 0, 0, 0, 0, 0])
                if ierr:
                    self.logger.debug('ERROR: Load not updated')
        return

    def update_federate_time(self, t):
        grantedtime = self.hi.request_time(t)
        return grantedtime

    def publish_bus_voltages(self, t, bus_subsystem_id):
        bus_data = self.get_bus_data(t, bus_subsystem_id)
        self.hi.publish(bus_data)
        return

    def get_bus_data(self, t, bus_subsystem_id):
        bus_data_formated = []
        ierr, rarray = self.PSSE.abusint(bus_subsystem_id, 1, 'NUMBER')

        bus_numbers = rarray[0]
        ierr, bus_data = self.PSSE.abusreal(bus_subsystem_id, 1, ['PU', 'ANGLED', 'MISMATCH'])

        if ierr:
            self.logger.warning('Unable to read voltage data at time {} (seconds)'.format(t))
        bus_data = np.array(bus_data)

        for i,j in enumerate(bus_numbers):
            bus_data_formated.append([j, bus_data[0, i], bus_data[1, i], bus_data[2, i]])
        return bus_data_formated

    def build_contingencies(self):
        contingencies = c.build_contingencies(self.PSSE, self.settings, self.logger)
        return contingencies

    def update_contingencies(self, t):
        for c_name, c in self.contingencies.items():
            c.update(t)

    def __del__(self):
        if not self.initComplete:
            self.logger.error("A valid PSS/E license not found. License may currently be in use.")

if __name__ == '__main__':
    #x = pyPSSE_instance(r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model\Settings\pyPSSE_settings.toml')
    x = pyPSSE_instance(
        r'C:\NAERM-global\PSSE_studycase\PSSE_WECC_model\Settings\pyPSSE_settings.toml')
    x.init()
    x.run()
    #
