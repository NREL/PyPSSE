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
        
        self.load_setup_files()
        self.convert_load()
        
        
        ierr = self.PSSE.rstr(str(self.settings.simulation.snp_file))
        assert ierr == 0, "error={}".format(ierr)
         
        # The following logic only runs when the helics interface is enabled
        self.disable_load_models_for_coupled_buses()
        self.disable_generation_for_coupled_buses()
        # self.save_model()
        ############# ------------------------------------- ###############
        
        ierr = self.PSSE.strt_2([0, 1],  str(self.settings.export.outx_file))

        if ierr==1:
            self.PSSE.cong(0)
            ierr = self.PSSE.strt_2([0, 1], str(self.settings.export.outx_file))
            assert ierr == 0, "error={}".format(ierr)
        
        elif ierr >1:
            raise Exception("Error starting simulation")

        self.load_user_defined_models()

        if self.settings.helics and self.settings.helics.cosimulation_mode:
            if self.settings.helics.iterative_mode:
                sim_step = self.settings.simulation.psse_solver_timestep.total_seconds() / self.iter_const
            else:
                sim_step = self.settings.simulation.psse_solver_timestep.total_seconds()
        else:
            sim_step = self.settings.simulation.psse_solver_timestep.total_seconds() 

        for mdl in self.settings["Simulation"]["User models"]:
            dll_path = os.path.join(self.settings["Simulation"]["Project Path"], 'Case_study', mdl)
            self.PSSE.addmodellibrary(dll_path)
            self.logger.debug('User defined library added: {}'.format(mdl))

        self.PSSE.dynamics_solution_param_2(
            [60, self._i, self._i, self._i, self._i, self._i, self._i, self._i],
            [0.4, self._f, sim_step, self._f, self._f, self._f, self._f, self._f]
        )

        self.PSSE.delete_all_plot_channels()

        self.setup_all_channels()
        
        self.logger.debug('pyPSSE initialization complete!')
        self.initialization_complete = True
        return self.initialization_complete

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
