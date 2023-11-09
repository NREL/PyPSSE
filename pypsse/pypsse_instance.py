# -*- coding:utf-8 -*-
"""
@author:Aadil Latif
@file:pyPSSE.py
@time:2/4/2020
"""

from pypsse.common import (
    SETTINGS_FOLDER,
    EXPORTS_SETTINGS_FILENAME,
    LOGS_FOLDER,
)
from pypsse.profile_manager.profile_store import ProfileManager
from pypsse.helics_interface import helics_interface
from pypsse.result_container import container
from pypsse.models import SimulationSettings
from pypsse.parsers import gic_parser as gp
import pypsse.simulation_controller as sc
from pypsse.parsers import reader as rd
import pypsse.pypsse_logger as Logger
import pypsse.contingencies as c

from pathlib import Path
import pandas as pd
import numpy as np
import subprocess
import os, sys
import shutil
import toml
import time

from pypsse.models import SimulationModes, ExportFileOptions, Contingencies


USING_NAERM = 0


class pyPSSE_instance:
    def __init__(self, settings_toml_path="", psse_path=""):
        settings = self.read_settings(settings_toml_path)
        self.settings = SimulationSettings.validate(settings)

        export_settings_path = (
            self.settings.simulation.project_path / EXPORTS_SETTINGS_FILENAME
        )
        assert (
            export_settings_path.exists()
        ), f"{export_settings_path} does nor exist"
        export_settings = self.read_settings(export_settings_path)
        self.export_settings = ExportFileOptions.validate(export_settings)

        log_path = os.path.join(
            self.settings.simulation.project_path, LOGS_FOLDER
        )
        self.logger = Logger.getLogger(
            "pyPSSE", log_path, LoggerOptions=self.settings.log
        )
        self.logger.debug("Starting PSSE instance")

        if psse_path != "" and Path(psse_path).exists():
            self.settings.simulation.psse_path = Path(psse_path)
            sys.path.append(psse_path)
            os.environ["PATH"] += ";" + psse_path
        else:
            sys.path.append(str(self.settings.simulation.psse_path))
            os.environ["PATH"] += ";" + str(self.settings.simulation.psse_path)

        try:
            nBus = 200000
            if "psse34" in str(self.settings.simulation.psse_path).lower():
                self.logger.debug('Instantiating psse version 34')
                import psse34
            elif "psse35" in str(self.settings.simulation.psse_path).lower():
                self.logger.debug('Instantiating psse version 35')
                import psse35
            else:
                self.logger.debug('Instantiating psse version 36')
                import psse36
            import psspy
            import dyntools

            self.dyntools = dyntools
            self.PSSE = psspy
            # self.logger.debug('Initializing PSS/E. connecting to license server')
            ierr = self.PSSE.psseinit(nBus)

            self.PSSE.psseinit(nBus)
            self.initComplete = True
            self.message = "success"

            self.start_simulation()
            self.init()
        except:
            raise Exception(
                "A valid PSS/E license not found. License may currently be in use."
            )

    def dump_settings(self, dest_dir):
        setting_toml_file = os.path.join(
            os.path.dirname(__file__), "defaults", "pyPSSE_settings.toml"
        )
        export_toml_file = os.path.join(
            os.path.dirname(__file__), "defaults", "export_settings.toml"
        )
        shutil.copy(setting_toml_file, dest_dir)
        shutil.copy(export_toml_file, dest_dir)

    def start_simulation(self):
        self.hi = None
        self.simStartTime = time.time()

        # ** Initialize PSSE modules

        if self.settings.simulation.case_study.exists():
            self.PSSE.case(str(self.settings.simulation.case_study))
        elif self.settings.simulation.raw_file.exists():
            self.PSSE.read(0, str(self.settings.simulation.raw_file))
        else:
            raise Exception(
                "Please pass a RAW or SAV file in the settings dictionary"
            )

        self.logger.info(
            f"Trying to read a file >>{self.settings.simulation.case_study}"
        )
        self.raw_data = rd.Reader(self.PSSE, self.logger)
        (
            self.bus_subsystems,
            self.all_subsysten_buses,
        ) = self.define_bus_subsystems()

        if self.export_settings.defined_subsystems_only:
            validBuses = self.all_subsysten_buses
        else:
            validBuses = self.raw_data.buses

        self.sim = sc.sim_controller(
            self.PSSE,
            self.dyntools,
            self.settings,
            self.export_settings,
            self.logger,
            validBuses,
            self.raw_data,
        )

        self.contingencies = self.build_contingencies()

        if self.settings.helics and self.settings.helics.cosimulation_mode:
            if self.settings.simulation.simulation_mode in [
                SimulationModes.DYNAMIC,
                SimulationModes.SNAP,
            ]:
                # self.sim.break_loads()
                ...
            self.hi = helics_interface(
                self.PSSE,
                self.sim,
                self.settings,
                self.export_settings,
                self.bus_subsystems,
                self.logger,
            )
            self.publications = self.hi.register_publications(
                self.bus_subsystems
            )
            if self.settings.helics.create_subscriptions:
                self.subscriptions = self.hi.register_subscriptions(
                    self.bus_subsystems
                )

        if self.settings.simulation.gic_file:
            self.network_graph = self.parse_GIC_file()
            self.bus_ids = self.network_graph.nodes.keys()
        else:
            self.network_graph = None

        self.results = container(self.settings, self.export_settings)
        self.exp_vars = self.results.get_export_variables()
        self.inc_time = True

        return

    def init(self):
        sucess = self.sim.init(self.bus_subsystems)
        # if sucess:
        #     self.load_info = self.sim.load_info
        # else:
        #     self.load_info = None

        if self.settings.simulation.use_profile_manager:
            self.pm = ProfileManager(None, self.sim, self.settings, self.logger)
            self.pm.setup_profiles()
        if self.settings.helics and self.settings.helics.cosimulation_mode:
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
            raise Exception(
                "Number of subsystems can not be more that 12. See PSSE documentation"
            )

        all_subsysten_buses = []
        for i, buses in enumerate(bus_subsystems):
            if not buses:
                continue

            all_subsysten_buses.extend(buses)
            ierr = self.PSSE.bsysinit(i)
            if ierr:
                raise Exception("Failed to create bus subsystem chosen buses.")
            else:
                self.logger.debug('Bus subsystem "{}" created'.format(i))

            ierr = self.PSSE.bsys(sid=i, numbus=len(buses), buses=buses)
            if ierr:
                raise Exception("Failed to add buses to bus subsystem.")
            else:
                bus_subsystems_dict[i] = buses
                self.logger.debug(
                    'Buses {} added to subsystem "{}"'.format(buses, i)
                )
        all_subsysten_buses = [str(x) for x in all_subsysten_buses]
        return bus_subsystems_dict, all_subsysten_buses

    def get_bus_indices(self):
        if self.settings.bus_subsystems.from_file:
            bus_file = self.settings.bus_subsystems.bus_file
            bus_info = pd.read_csv(bus_file, index_col=None)
            bus_info = bus_info.values
            r, c = bus_info.shape
            bus_data = []
            for col in range(c):
                data = [int(x) for x in bus_info[:, col] if not np.isnan(x)]
                bus_data.append(data)
        else:
            bus_data = self.settings.bus_subsystems.bus_subsystem_list
        return bus_data

    def read_settings(self, settings_toml_path):
        settings_text = ""
        f = open(settings_toml_path, "r")
        text = settings_text.join(f.readlines())
        toml_data = toml.loads(text)
        toml_data = {
            str(k): (str(v) if isinstance(v, str) else v)
            for k, v in toml_data.items()
        }
        f.close()
        return toml_data

    def run(self):
        if self.sim.initialization_complete:
            if self.settings.plots and self.settings.plots.enable_dynamic_plots:
                bokeh_server_proc = subprocess.Popen(
                    ["bokeh", "serve"], stdout=subprocess.PIPE
                )
            else:
                bokeh_server_proc = None
            # self.initialize_loads()
            self.logger.debug(
                "Running dynamic simulation for time {} sec".format(
                    self.settings.simulation.simulation_time.total_seconds()
                )
            )
            T = self.settings.simulation.simulation_time.total_seconds()
            t = 0
            while True:
                self.step(t)
                if self.inc_time:
                    t += (
                        self.settings.simulation.simulation_step_resolution.total_seconds()
                    )
                if t >= T:
                    break

            self.PSSE.pssehalt_2()
            if not self.export_settings.export_results_using_channels:
                self.results.export_results()
            else:
                self.sim.export()

            if bokeh_server_proc != None:
                bokeh_server_proc.terminate()
        else:
            self.logger.error(
                "Run init() command to initialize models before running the simulation"
            )
        return

    def get_bus_ids(self):
        ierr, iarray = self.PSSE.abusint(-1, 1, "NUMBER")
        return iarray

    def step(self, t):
        self.update_contingencies(t)
        if self.settings.simulation.use_profile_manager:
            self.pm.update()
        ctime = time.time() - self.simStartTime
        self.logger.debug(
            f"Simulation time: {t} seconds; Run time: {ctime}; pyPSSE time: {self.sim.getTime()}"
        )
        if self.settings.helics and self.settings.helics.cosimulation_mode:
            if self.settings.helics.create_subscriptions:
                self.update_subscriptions()
                self.logger.debug("Time requested: {}".format(t))
                self.inc_time, helics_time = self.update_federate_time(t)
                self.logger.debug("Time granted: {}".format(helics_time))

        if self.inc_time:
            a = self.sim.step(t)
        else:
            self.sim.resolveStep(t)

        if self.settings.helics and self.settings.helics.cosimulation_mode:
            self.publish_data()
        if self.export_settings.defined_subsystems_only:
            curr_results = self.sim.read_subsystems(
                self.exp_vars, self.all_subsysten_buses
            )
        else:
            curr_results = self.sim.read_subsystems(
                self.exp_vars, self.raw_data.buses
            )
            # curr_results = self.sim.read(self.exp_vars, self.raw_data)

        if not USING_NAERM:
            if (
                self.inc_time
                and not self.export_settings.export_results_using_channels
            ):
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
        curr_results = (
            self.sim.read_subsystems(self.exp_vars, self.all_subsysten_buses)
            if self.export_settings.defined_subsystems_only
            else self.sim.read_subsystems(self.exp_vars, self.raw_data.buses)
        )
        # class_name = list(params.keys())[0]
        return curr_results
        # restruct_results = self.restructure_results(curr_results, class_name)
        # return curr_results, restruct_results

    def restructure_results(self, results, class_name):
        # cNames = []
        pNames = []
        Data = []
        Bus_ID = []
        Id = []
        ckt_id = []
        to_bus = []
        to_bus2 = []
        for class_ppty, vdict in results.items():
            if len(class_ppty.split("_")) == 3:
                cName = (
                    class_ppty.split("_")[0] + "_" + class_ppty.split("_")[1]
                )
                pName = class_ppty.split("_")[2]
            else:
                cName = class_ppty.split("_")[0]
                pName = class_ppty.split("_")[1]
            if cName == class_name:
                # cNames.append(cName)
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
                        if len(k.split("_")) == 2:
                            Bus_ID.append(k.split("_")[1])
                            Id.append(k.split("_")[0])
                        if len(k.split("_")) == 3:
                            Bus_ID.append(k.split("_")[0])
                            ckt_id.append(k.split("_")[2])
                            to_bus.append(k.split("_")[1])
                        if len(k.split("_")) == 4:
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
        ierr, rarray = self.PSSE.abusint(bus_subsystem_id, 1, "NUMBER")

        bus_numbers = rarray[0]
        ierr, bus_data = self.PSSE.abusreal(
            bus_subsystem_id, 1, ["PU", "ANGLED", "MISMATCH"]
        )

        if ierr:
            self.logger.warning(
                "Unable to read voltage data at time {} (seconds)".format(t)
            )
        bus_data = np.array(bus_data)

        for i, j in enumerate(bus_numbers):
            bus_data_formated.append(
                [j, bus_data[0, i], bus_data[1, i], bus_data[2, i]]
            )
        return bus_data_formated

    def build_contingencies(self):
        contingencies = c.build_contingencies(
            self.PSSE, self.settings, self.logger
        )
        return contingencies

    def update_contingencies(self, t):
        for c in self.contingencies:
            c.update(t)

    def inject_contingencies_external(self, temp):
        print("external settings : ", temp, flush=True)
        contingencies = c.build_contingencies(self.PSSE, Contingencies.validate(temp), self.logger)
        self.contingencies.extend(contingencies)

    def __del__(self):
        if hasattr(self, "PSSE"):
            self.PSSE.pssehalt_2()


if __name__ == "__main__":
    # x = pyPSSE_instance(r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model\Settings\simulation_settings.toml')
    x = pyPSSE_instance(
        r"C:\Users\alatif\Desktop\PYPSSE\examples\dynamic_example\Settings\simulation_settings.toml"
    )
    x.init()
    for i in range(10):
        t = i / 240.0
        res = x.step(t)
        res = x.get_results({"Buses": ["PU", "FREQ"]})

    # scenarios = [14203, 14303, 14352, 15108, 15561, 17604, 17605, 37102, 37124, 37121]
    # for s in scenarios:
    #     x = pyPSSE_instance(f'C:\\Users\\alatif\\Desktop\\Naerm\\PyPSSE\\TransOnly\\Settings\{s}.toml')
    #     x.init()
    #     x.run()
    #     del x
    #     os.rename(
    #         r'C:\Users\alatif\Desktop\Naerm\PyPSSE\TransOnly\Exports\Simulation_results.hdf5',
    #         f'C:\\Users\\alatif\\Desktop\\Naerm\\PyPSSE\\TransOnly\\Exports\\{s}.hdf5')
