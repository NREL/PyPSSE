"""
@author:Aadil Latif
@file:pyPSSE.py
@time:2/4/2020
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import toml

import pypsse.contingencies as c
import pypsse.custom_logger as logger
import pypsse.simulation_controller as sc
from pypsse.common import EXPORTS_SETTINGS_FILENAME, LOGS_FOLDER, MAX_PSSE_BUSSYSTEMS
from pypsse.enumerations import SimulationStatus
from pypsse.helics_interface import HelicsInterface
from pypsse.models import ExportFileOptions, SimulationModes, SimulationSettings
from pypsse.parsers import gic_parser as gp
from pypsse.parsers import reader as rd
from pypsse.profile_manager.profile_store import ProfileManager
from pypsse.result_container import Container

USING_NAERM = 0


class Simulator:
    "Base class for the simulator"

    _status: SimulationStatus = SimulationStatus.NOT_INITIALIZED

    def __init__(self, settings_toml_path="", psse_path=""):
        "Load a valid PyPSSE project and sets up simulation"
        self._status = SimulationStatus.STARTING_INSTANCE
        settings = self.read_settings(settings_toml_path)
        self.settings = SimulationSettings.model_validate(settings)
        export_settings_path = self.settings.simulation.project_path / EXPORTS_SETTINGS_FILENAME
        assert export_settings_path.exists(), f"{export_settings_path} does nor exist"
        export_settings = self.read_settings(export_settings_path)
        self.export_settings = ExportFileOptions.model_validate(export_settings)

        log_path = os.path.join(self.settings.simulation.project_path, LOGS_FOLDER)
        self.logger = logger.get_logger("pyPSSE", log_path, logger_options=self.settings.log)
        self.logger.debug("Starting PSSE instance")

        if psse_path != "" and Path(psse_path).exists():
            self.settings.simulation.psse_path = Path(psse_path)
            sys.path.append(psse_path)
            os.environ["PATH"] += ";" + psse_path
        else:
            sys.path.append(str(self.settings.simulation.psse_path))
            os.environ["PATH"] += ";" + str(self.settings.simulation.psse_path)

        n_bus = 200000
        if "psse34" in str(self.settings.simulation.psse_path).lower():
            self.logger.debug("Instantiating psse version 34")
            import psse34  # noqa: F401
        elif "psse35" in str(self.settings.simulation.psse_path).lower():
            self.logger.debug("Instantiating psse version 35")
            import psse35  # noqa: F401
        else:
            self.logger.debug("Instantiating psse version 36")
            import psse36  # noqa: F401
        import dyntools
        import psspy

        self.dyntools = dyntools
        self.psse = psspy
        # self.logger.debug('Initializing PSS/E. connecting to license server')
        ierr = self.psse.psseinit(n_bus)
        assert ierr == 0, f"Error code: {ierr}"
        self.psse.psseinit(n_bus)

        self.start_simulation()
        self.init()
        self._status = SimulationStatus.INITIALIZATION_COMPLETE

    def dump_settings(self, dest_dir):
        setting_toml_file = os.path.join(os.path.dirname(__file__), "defaults", "pyPSSE_settings.toml")
        export_toml_file = os.path.join(os.path.dirname(__file__), "defaults", "export_settings.toml")
        shutil.copy(setting_toml_file, dest_dir)
        shutil.copy(export_toml_file, dest_dir)

    def start_simulation(self):
        "Starts a loaded simulation"
        self.hi = None
        self.simStartTime = time.time()

        if self.settings.simulation.case_study.exists():
            self.psse.case(str(self.settings.simulation.case_study))
        elif self.settings.simulation.raw_file.exists():
            self.psse.read(0, str(self.settings.simulation.raw_file))
        else:
            msg = "Please pass a RAW or SAV file in the settings dictionary"
            raise Exception(msg)

        self.logger.info(f"Trying to read a file >>{self.settings.simulation.case_study}")
        self.raw_data = rd.Reader(self.psse, self.logger)
        (
            self.bus_subsystems,
            self.all_subsysten_buses,
        ) = self.define_bus_subsystems()

        if self.export_settings.defined_subsystems_only:
            valid_buses = self.all_subsysten_buses
        else:
            valid_buses = self.raw_data.buses

        self.sim = sc.sim_controller(
            self.psse,
            self.dyntools,
            self.settings,
            self.export_settings,
            self.logger,
            valid_buses,
            self.raw_data,
        )

        self.contingencies = self.build_contingencies()

        if self.settings.helics and self.settings.helics.cosimulation_mode:
            if self.settings.simulation.simulation_mode in [
                SimulationModes.DYNAMIC,
                SimulationModes.SNAP,
            ]:
                ...
            self.hi = HelicsInterface(
                self.psse,
                self.sim,
                self.settings,
                self.export_settings,
                self.bus_subsystems,
                self.logger,
            )
            self.publications = self.hi.register_publications(self.bus_subsystems)
            if self.settings.helics.create_subscriptions:
                self.subscriptions = self.hi.register_subscriptions()

        if self.settings.simulation.gic_file:
            self.network_graph = self.parse_gic_file()
            self.bus_ids = self.network_graph.nodes.keys()
        else:
            self.network_graph = None

        self.results = Container(self.settings, self.export_settings)
        self.exp_vars = self.results.get_export_variables()
        self.inc_time = True

    def init(self):
        "Initializes the model"

        self.sim.init(self.bus_subsystems)

        if self.settings.simulation.use_profile_manager:
            self.pm = ProfileManager(None, self.sim, self.settings, self.logger)
            self.pm.setup_profiles()
        if self.settings.helics and self.settings.helics.cosimulation_mode:
            self.hi.enter_execution_mode()

    def parse_gic_file(self):
        "Parses the GIC file (if included in the project)"

        gicdata = gp.GICParser(self.settings, self.logger)
        return gicdata.psse_graph

    def define_bus_subsystems(self):
        "Defines a bussystem in the loaded PSSE model"

        bus_subsystems_dict = {}
        bus_subsystems = self.get_bus_indices()
        # valid bus subsystem ID. Valid bus subsystem IDs range from 0 to 11 (PSSE documentation)
        if len(bus_subsystems) > MAX_PSSE_BUSSYSTEMS:
            msg = "Number of subsystems can not be more that 12. See PSSE documentation"
            raise Exception(msg)

        all_subsysten_buses = []
        for i, buses in enumerate(bus_subsystems):
            if not buses:
                continue

            all_subsysten_buses.extend(buses)
            ierr = self.psse.bsysinit(i)
            if ierr:
                msg = "Failed to create bus subsystem chosen buses."
                raise Exception(msg)
            else:
                self.logger.debug(f'Bus subsystem "{i}" created')

            ierr = self.psse.bsys(sid=i, numbus=len(buses), buses=buses)
            if ierr:
                msg = "Failed to add buses to bus subsystem."
                raise Exception(msg)
            else:
                bus_subsystems_dict[i] = buses
                self.logger.debug(f'Buses {buses} added to subsystem "{i}"')
        all_subsysten_buses = [str(x) for x in all_subsysten_buses]
        return bus_subsystems_dict, all_subsysten_buses

    def get_bus_indices(self):
        "Retuens bus indices for bus subsystems"

        if self.settings.bus_subsystems.from_file:
            bus_file = self.settings.bus_subsystems.bus_file
            bus_info = pd.read_csv(bus_file, index_col=None)
            bus_info = bus_info.values
            _, n_cols = bus_info.shape
            bus_data = []
            for col in range(n_cols):
                data = [int(x) for x in bus_info[:, col] if not np.isnan(x)]
                bus_data.append(data)
        else:
            bus_data = self.settings.bus_subsystems.bus_subsystem_list
        return bus_data

    def read_settings(self, settings_toml_path):
        "Read the user defined settings"

        settings_text = ""
        f = open(settings_toml_path)
        text = settings_text.join(f.readlines())
        toml_data = toml.loads(text)
        toml_data = {str(k): (str(v) if isinstance(v, str) else v) for k, v in toml_data.items()}
        f.close()
        return toml_data

    def run(self):
        "Launches the simulation"
        self._status = SimulationStatus.RUNNING_SIMULATION
        if self.sim.initialization_complete:
            if self.settings.plots and self.settings.plots.enable_dynamic_plots:
                bokeh_server_proc = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)  # noqa: S603,S607
            else:
                bokeh_server_proc = None

            self.logger.debug(
                f"Running dynamic simulation for time {self.settings.simulation.simulation_time.total_seconds()} sec"
            )
            total_simulation_time = self.settings.simulation.simulation_time.total_seconds()
            t = 0
            while True:
                self.step(t)
                if self.inc_time:
                    t += self.settings.simulation.simulation_step_resolution.total_seconds()
                if t >= total_simulation_time:
                    break

            self.psse.pssehalt_2()
            if not self.export_settings.export_results_using_channels:
                self.results.export_results()
            else:
                self.sim.export()

            if bokeh_server_proc is not None:
                bokeh_server_proc.terminate()
        else:
            self.logger.error("Run init() command to initialize models before running the simulation")
        self._status = "Simulation complete"

    def get_bus_ids(self):
        "Returns bus IDs"

        ierr, iarray = self.psse.abusint(-1, 1, "NUMBER")
        assert ierr == 0, f"Error code: {ierr}"
        return iarray

    def step(self, t):
        "Steps through a single simulation time step. Is called iteratively to increment the simualtion"
        self.update_contingencies(t)
        if self.settings.simulation.use_profile_manager:
            self.pm.update()
        ctime = time.time() - self.simStartTime
        self.logger.debug(f"Simulation time: {t} seconds; Run time: {ctime}; pyPSSE time: {self.sim.get_time()}")
        if self.settings.helics and self.settings.helics.cosimulation_mode:
            if self.settings.helics.create_subscriptions:
                self.update_subscriptions()
                self.logger.debug(f"Time requested: {t}")
                self.inc_time, helics_time = self.update_federate_time(t)
                self.logger.debug(f"Time granted: {helics_time}")

        if self.inc_time:
            self.sim.step(t)
        else:
            self.sim.resolve_step()

        if self.settings.helics and self.settings.helics.cosimulation_mode:
            self.publish_data()

        curr_results = self.update_result_container(t)
        return curr_results

    def update_result_container(self, t):
        if self.export_settings.defined_subsystems_only:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.all_subsysten_buses)
        else:
            curr_results = self.sim.read_subsystems(self.exp_vars, self.raw_data.buses)

        if not USING_NAERM:
            if not self.export_settings.export_results_using_channels:
                self.results.update(curr_results, t, self.sim.get_time(), self.sim.has_converged())
        return curr_results

    def update_subscriptions(self):
        "Updates subscriptions (co-simulation mode only)"

        self.hi.subscribe()

    def update_federate_time(self, t):
        "Makes a time request to teh HELICS broker (co-simulation mode only)"

        inc_time, curr_time = self.hi.request_time(t)
        return inc_time, curr_time

    def publish_data(self):
        "Updates publications (co-simulation mode only)"
        self.hi.publish()

    def get_results(self, params):
        "Returns queried simulation results"
        self._status = SimulationStatus.STARTING_RESULT_EXPORT
        self.exp_vars = self.results.update_export_variables(params)
        curr_results = (
            self.sim.read_subsystems(self.exp_vars, self.all_subsysten_buses)
            if self.export_settings.defined_subsystems_only
            else self.sim.read_subsystems(self.exp_vars, self.raw_data.buses)
        )
        self._status = SimulationModes.RESULT_EXPORT_COMPLETE
        return curr_results

    def status(self):
        return self._status.value

    def restructure_results(self, results, class_name):
        "Restructure results for the improved user experience"

        # c_names = []
        p_names = []
        data = []
        bud_id = []
        uuid = []
        ckt_id = []
        to_bus = []
        to_bus2 = []
        for class_ppty, v_dict in results.items():
            if len(class_ppty.split("_")) == 3:  # noqa: PLR2004
                c_name = class_ppty.split("_")[0] + "_" + class_ppty.split("_")[1]
                p_name = class_ppty.split("_")[2]
            else:
                c_name = class_ppty.split("_")[0]
                p_name = class_ppty.split("_")[1]
            if c_name == class_name:
                # c_names.append(c_name)
                p_names.append(p_name)
                keys = list(v_dict.keys())
                bud_id = []
                ckt_id = []
                uuid = []
                to_bus = []
                to_bus2 = []

                for k_raw in keys:
                    k = str(k_raw)
                    if "_" in k:
                        if len(k.split("_")) == 2:  # noqa: PLR2004
                            bud_id.append(k.split("_")[1])
                            uuid.append(k.split("_")[0])
                        if len(k.split("_")) == 3:  # noqa: PLR2004
                            bud_id.append(k.split("_")[0])
                            ckt_id.append(k.split("_")[2])
                            to_bus.append(k.split("_")[1])
                        if len(k.split("_")) == 4:  # noqa: PLR2004
                            bud_id.append(k.split("_")[0])
                            ckt_id.append(k.split("_")[3])
                            to_bus.append(k.split("_")[1])
                            to_bus2.append(k.split("_")[2])
                    else:
                        bud_id.append(k)
                data.append(list(v_dict.values()))
        return p_names, bud_id, uuid, to_bus, to_bus2, ckt_id, data

    def get_bus_data(self, t, bus_subsystem_id):
        "Return bus data"

        bus_data_formated = []
        ierr, rarray = self.psse.abusint(bus_subsystem_id, 1, "NUMBER")
        assert ierr == 0, f"Error code: {ierr}"
        bus_numbers = rarray[0]
        ierr, bus_data = self.psse.abusreal(bus_subsystem_id, 1, ["PU", "ANGLED", "MISMATCH"])
        assert ierr == 0, f"Error code: {ierr}"
        if ierr:
            self.logger.warning(f"Unable to read voltage data at time {t} (seconds)")
        bus_data = np.array(bus_data)

        for i, j in enumerate(bus_numbers):
            bus_data_formated.append([j, bus_data[0, i], bus_data[1, i], bus_data[2, i]])
        return bus_data_formated

    def build_contingencies(self):
        "Builds user defined contengingies"

        contingencies = c.build_contingencies(self.psse, self.settings, self.logger)
        return contingencies

    def update_contingencies(self, t):
        "Updates contingencies during the simualtion run"
        for contingency in self.contingencies:
            contingency.update(t)

    def __del__(self):
        if hasattr(self, "PSSE"):
            self.psse.pssehalt_2()
