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
from pypsse.ProfileManager.ProfileStore import ProfileManager
from pypsse.helics_interface import helics_interface
from pypsse.result_container import container
from pypsse.Parsers import gic_parser as gp
import pypsse.simulation_controller as sc
from pypsse.Parsers import reader as rd
import pypsse.pyPSSE_logger as Logger
import pypsse.contingencies as c
import pandas as pd
import numpy as np
import subprocess
import os, sys
import toml
import time
import shutil

USING_NAERM = 1

class pyPSSE_instance:

    def __init__(self, settinigs_toml_path='', psse_path=''):
      
        if psse_path != '':
            sys.path.append(psse_path)
            os.environ['PATH'] += ';' + psse_path

        else:
        
            self.settings = self.read_settings(settinigs_toml_path)
            if self.settings["Simulation"]["Simulation mode"] == "Dynamic":
                assert self.settings["Simulation"]["Use profile manager"] == False,\
                    "Profile manager can not be used for dynamic simulations. Set 'Use profile manager' to False"


            sys.path.append(self.settings["Simulation"]["PSSE_path"])
            os.environ['PATH'] += ';' + self.settings["Simulation"]["PSSE_path"]

        
        try:
            nBus = 200000
            import psse34
            import psspy
            import dyntools

            self.dyntools = dyntools
            self.PSSE = psspy
            # self.logger.debug('Initializing PSS/E. connecting to license server')
            ierr = self.PSSE.psseinit(nBus)

            self.PSSE.psseinit(nBus)
            self.initComplete = True
            self.message = 'success'

            if settinigs_toml_path != '':
                self.read_allsettings(settinigs_toml_path)
                self.start_simulation()
        except:
            raise Exception("A valid PSS/E license not found. License may currently be in use.")


    def dump_settings(self, dest_dir):

        setting_toml_file = os.path.join(os.path.dirname(__file__), 'defaults', 'pyPSSE_settings.toml' )
        export_toml_file = os.path.join(os.path.dirname(__file__), 'defaults', 'export_settings.toml' )
        shutil.copy(setting_toml_file, dest_dir)
        shutil.copy(export_toml_file, dest_dir)
    
    def read_allsettings(self,settinigs_toml_path):

        self.settings = self.read_settings(settinigs_toml_path)
        export_settings_path = os.path.join(
            self.settings["Simulation"]["Project Path"], 'Settings', 'export_settings.toml'
        )
        self.export_settings = self.read_settings(export_settings_path)


    def start_simulation(self):
        self.hi = None
        self.simStartTime = time.time()

        log_path = os.path.join(self.settings["Simulation"]["Project Path"], 'Logs')
        self.logger = Logger.getLogger('pyPSSE', log_path, LoggerOptions=self.settings["Logging"])
        self.logger.debug('Starting PSSE instance')
        #** Initialize PSSE modules

        self.PSSE.case(
            os.path.join(self.settings["Simulation"]["Project Path"],
                         "Case_study",
                         self.settings["Simulation"]["Case study"])
        )
        self.logger.info(f"Trying to read a file >>{os.path.join(self.settings['Simulation']['Project Path'],'Case_study',self.settings['Simulation']['Case study'])}")

        self.raw_data = rd.Reader(self.PSSE, self.logger)
        self.bus_subsystems, self.all_subsysten_buses = self.define_bus_subsystems()
        if self.export_settings['Defined bus subsystems only']:
            validBuses = self.all_subsysten_buses
        else:
            validBuses = self.raw_data.buses
        self.sim = sc.sim_controller(self.PSSE, self.dyntools, self.settings, self.export_settings, self.logger, validBuses)

        self.contingencies = self.build_contingencies()

        if self.settings["HELICS"]["Cosimulation mode"]:
            self.hi = helics_interface(
                self.PSSE, self.sim, self.settings, self.export_settings, self.bus_subsystems, self.logger
            )
            self.publications = self.hi.register_publications(self.bus_subsystems)
            if self.settings["HELICS"]["Create subscriptions"]:
                self.subscriptions = self.hi.register_subscriptions(self.bus_subsystems)
        if self.settings["Simulation"]["GIC file"]:
            self.network_graph = self.parse_GIC_file()
            self.bus_ids = self.network_graph.nodes.keys()
        else:
            self.network_graph = None

        self.results = container(self.settings, self.export_settings)
        self.exp_vars = self.results.get_export_variables()
        self.inc_time = True

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
        # if sucess:
        #     self.load_info = self.sim.load_info
        # else:
        #     self.load_info = None

        if self.settings["Simulation"]["Use profile manager"]:
            self.pm = ProfileManager(None, self.sim, self.settings, self.logger)
            self.pm.setup_profiles()
        if self.settings["HELICS"]["Cosimulation mode"]:
            print("trying helics execution")
            self.hi.enter_execution_mode()
            print(" helics execution ended")
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
            self.logger.debug('Running dynamic simulation for time {} sec'.format(
                self.settings["Simulation"]["Simulation time (sec)"])
            )
            self.logger.debug(
                'Simulation time step {} sec'.format(self.settings["Simulation"]["Step resolution (sec)"]))
            T = self.settings["Simulation"]["Simulation time (sec)"]
            t = 0
            self.test = False
            while True:
                dT = self.check_contingency_updates(t)
                if dT:
                    T += dT
                self.step(t)
                if self.inc_time:
                    t += self.settings["Simulation"]["Step resolution (sec)"]
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
        if self.settings["Simulation"]["Use profile manager"]:
            self.pm.update()
        ctime = time.time() - self.simStartTime
        self.logger.debug(f'Simulation time: {t} seconds; Run time: {ctime}; pyPSSE time: {self.sim.getTime()}')
        if self.settings["HELICS"]["Cosimulation mode"]:
            if self.settings["HELICS"]["Create subscriptions"]:
                print("Here")
                self.update_subscriptions()
                self.logger.debug('Time requested: {}'.format(t))
                self.inc_time, helics_time = self.update_federate_time(t)
                self.logger.debug('Time granted: {}'.format(helics_time))

        if self.inc_time:
            self.sim.step(t)
        else:
            self.sim.resolveStep()

        if self.settings["HELICS"]["Cosimulation mode"]:
            self.publish_data()
        if self.export_settings['Defined bus subsystems only']:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.all_subsysten_buses)
        else:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.raw_data.buses)
            #curr_results = self.sim.read(self.exp_vars, self.raw_data)
        if not USING_NAERM:
            if self.inc_time and not self.export_settings["Export results using channels"]:
                self.results.Update(curr_results, None, t, self.sim.getTime())
        return curr_results

    def update_subscriptions(self):
        data = self.hi.subscribe()
        return

    def update_federate_time(self, t):
        inc_time, curr_time = self.hi.request_time(t)
        return inc_time, curr_time

    def publish_data(self):
        self.hi.publish()
        return

    def get_results(self, params):
        self.exp_vars = self.results.update_export_variables(params)
        if self.export_settings['Defined bus subsystems only']:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.all_subsysten_buses)
        else:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.raw_data.buses)
            #curr_results = self.sim.read(self.exp_vars, self.raw_data)
        
        class_name = list(params.keys())[0]
        #for x in self.restructure_results(curr_results, class_name):
            #print(x)
        restruct_results = self.restructure_results(curr_results, class_name)
        return curr_results, restruct_results

    def restructure_results(self, results, class_name):
        #cNames = []
        pNames = []
        Data = []
        Bus_ID = []
        Id = []
        ckt_id = []
        to_bus = []
        to_bus2 = []
        #print(results)
        for class_ppty, vdict in results.items():
            if len(class_ppty.split("_"))==3:
                cName = class_ppty.split("_")[0] + '_' + class_ppty.split("_")[1] 
                pName = class_ppty.split("_")[2]
            else:
                cName = class_ppty.split("_")[0]
                pName = class_ppty.split("_")[1]
            if cName == class_name:
                #cNames.append(cName)
                pNames.append(pName)
                keys = list(vdict.keys())
                Bus_ID = []
                ckt_id = []
                Id = []
                to_bus = []
                to_bus2 = []

                for k in keys:
                    k = str(k)
                    if "_" in k:
                        if len(k.split('_'))==2:
                            Bus_ID.append(k.split("_")[1])
                            Id.append(k.split("_")[0])
                        if len(k.split('_'))==3:
                            Bus_ID.append(k.split("_")[0])
                            ckt_id.append(k.split("_")[2])
                            to_bus.append(k.split("_")[1])
                        if len(k.split('_'))==4:
                            Bus_ID.append(k.split("_")[0])
                            ckt_id.append(k.split("_")[3])
                            to_bus.append(k.split("_")[1])
                            to_bus2.append(k.split("_")[2])
                    else:
                        Bus_ID.append(k)
                Data.append(list(vdict.values()))
        return pNames, Bus_ID, Id, to_bus, to_bus2, ckt_id, Data

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

    def inject_contingencies_external(self,temp):
        print("external settings : ", temp , flush=True)
        contingencies = c.build_contingencies(self.PSSE, temp, self.logger)
        self.contingencies.update(contingencies)

if __name__ == '__main__':
    #x = pyPSSE_instance(r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model\Settings\pyPSSE_settings.toml')
    # scenarios = [14203, 14303, 14352, 15108, 15561, 17604, 17605, 37102, 37124, 37121]
    # for s in scenarios:
    #     x = pyPSSE_instance(f'C:\\Users\\alatif\\Desktop\\Naerm\\PyPSSE\\TransOnly\\Settings\{s}.toml')
    #     x.init()
    #     x.run()
    #     del x
    #     os.rename(
    #         r'C:\Users\alatif\Desktop\Naerm\PyPSSE\TransOnly\Exports\Simulation_results.hdf5',
    #         f'C:\\Users\\alatif\\Desktop\\Naerm\\PyPSSE\\TransOnly\\Exports\\{s}.hdf5')

    pass
