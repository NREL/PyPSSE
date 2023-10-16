from pypsse.modes.constants import converter, DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.modes.abstract_mode import AbstractMode
from pypsse.utils.dynamic_utils import DynamicUtils
import pandas as pd
import numpy as np
import datetime
import os
from pypsse.models import SimulationSettings, ExportSettings

class Snap(AbstractMode, DynamicUtils):

    def __init__(self,psse, dyntools, settings:SimulationSettings, export_settings:ExportSettings, logger, subsystem_buses, raw_data):
        super().__init__(psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
        self.time = settings.simulation.start_time
        self._StartTime = settings.simulation.start_time
        self.incTime = settings.simulation.simulation_step_resolution 
        self.init(subsystem_buses)
        return

    def init(self, bus_subsystems):
        super().init(bus_subsystems)

        self.iter_const = 100.0
        self.xTime = 0

        ierr = self.PSSE.case(str(self.settings.simulation.case_study))
        assert ierr == 0, "error={}".format(ierr)
        ierr = self.PSSE.rstr(str(self.settings.simulation.snp_file))
        assert ierr == 0, "error={}".format(ierr)
        ierr = self.PSSE.strt_2([0, 1],  str(self.settings.export.outx_file))

        #self.disable_load_models_for_coupled_buses()
        #self.disable_generation_for_coupled_buses()

        #self.save_model()

        if ierr==1:
            self.PSSE.cong(0)
            ierr = self.PSSE.strt_2([0, 1], str(self.settings.export.outx_file))
            assert ierr == 0, "error={}".format(ierr)
        
        elif ierr >1:
            raise Exception("Error starting simulation")

        if self.settings.helics.cosimulation_mode:
            if self.settings.helics.iterative_mode:
                sim_step = self.settings.simulation.psse_solver_timestep.total_seconds() / self.iter_const
            else:
                sim_step = self.settings.simulation.psse_solver_timestep.total_seconds()
        else:
            sim_step = self.settings.simulation.psse_solver_timestep.total_seconds() 

        self.load_setup_files()
        self.convert_load()
        self.load_user_defined_models()

        self.PSSE.dynamics_solution_param_2(
            [60, self._i, self._i, self._i, self._i, self._i, self._i, self._i],
            [0.4, self._f, sim_step, self._f, self._f, self._f, self._f, self._f]
        )

        self.PSSE.delete_all_plot_channels()

        self.setup_all_channels()
        

        self.logger.debug('pyPSSE initialization complete!')
        self.initialization_complete = True
        return self.initialization_complete

    def disable_generation_for_coupled_buses(self):
        if self.settings.helics.cosimulation_mode and self.settings.helics.disable_generation_on_coupled_buses:
            sub_data = pd.read_csv(self.settings.simulation.subscriptions_file)
            sub_data = sub_data[sub_data['element_type'] == 'Load']
            generators = {}
            for ix, row in sub_data.iterrows():
                bus = row['bus']
                for gen_bus, gen_id in self.raw_data.generators:
                    if gen_bus not in generators:
                        generators[bus] = [gen_id]
                    else:
                        generators[bus].append(gen_id)

            for bus_id, machines in generators.items():
                for machine in machines:
                    intgar = [0, self._i, self._i, self._i, self._i, self._i]
                    realar = [
                        self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f,
                        self._f, self._f, self._f, self._f, self._f, self._f, self._f, self._f
                    ]
                    self.PSSE.machine_chng_2(bus_id, machine, intgar, realar)
                    self.logger.info(f"Machine disabled: {bus_id}_{machine}")
        return

    def disable_load_models_for_coupled_buses(self):
        if self.settings.helics.cosimulation_mode:
            sub_data = pd.read_csv(self.settings.simulation.subscriptions_file)
            sub_data = sub_data[sub_data['element_type'] == 'Load']

            self.psse_dict = {}
            for ix, row in sub_data.iterrows():
                bus = row['bus']
                load = row['element_id']
                ierr = self.PSSE.ldmod_status(0, int(bus), str(load), 1, 0)
                self.logger.error(f"Dynamic model for load {load} connected to bus {bus} has been disabled")

    def step(self, t):
        self.time = self.time + self.incTime
        self.xTime = 0
        return self.PSSE.run(0, t, 1, 1, 1)

    def resolveStep(self, t):
        self.xTime += 1
        return self.PSSE.run(0, t + self.xTime * self.incTime / self.iter_const, 1, 1, 1)


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
                    'Load ID': load_data[0, i],
                    'Bus name': load_data[1, i],
                    'Bus name (ext)': load_data[2, i],
                }
            all_bus_ids[id] = load_info
        return all_bus_ids

    def getTime(self):
        return self.time

    def GetTotalSeconds(self):
        return (self.time - self._StartTime).total_seconds()

    def GetStepSizeSec(self):
        return self.settings.simulation.simulation_step_resolution.total_seconds()

    

    @converter
    def read_subsystems(self, quantities, subsystem_buses, ext_string2_info={}, mapping_dict={}):

        results = super(Snap, self).read_subsystems(
            quantities,
            subsystem_buses,
            mapping_dict=mapping_dict,
            ext_string2_info=ext_string2_info
        )

        poll_results = self.poll_channels()
        results.update(poll_results)
        """ Add """
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
                                            irr, con_index = getattr(self.PSSE, funcName)(int(bus), ld_id, 'CHARAC',
                                                                                          'CON')
                                            if con_index is not None:
                                                act_con_index = con_index + con_ind
                                                irr, value = self.PSSE.dsrval('CON', act_con_index)

                                                res_base = f"{class_name}_{v}"
                                                if res_base not in results:
                                                    results[res_base] = {}
                                                obj_name = f"{bus}_{ld_id}"
                                                results[res_base][obj_name] = value
            else:
                self.logger.warning("Extend function 'read_subsystems' in the Snap class (Snap.py)")

        return results
