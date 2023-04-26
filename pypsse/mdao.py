from pypsse.pypsse_instance import pyPSSE_instance
import openmdao.api as om
import logging

logger = logging.getLogger("model")

class PSSE:
    model_loaded = False
    
    def load_model(self, settings_file_path, psse_path):
        self.psse_obj = pyPSSE_instance(settings_file_path, psse_path)
        self.time_counter = 0
        self.psse_obj.init()
        self.model_loaded =True
    
    def solve_step(self):
        self.current_result = self.psse_obj.step(self.time_counter)
        self.time_counter += self.psse_obj.settings['Simulation']["Step resolution (sec)"]
        return self.current_result

    def export_result(self):
        if not self.psse_obj.export_settings["Export results using channels"]:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()

    def close_case(self):
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f'PSSE case {self.uuid} closed.')

    def get_property(self, model_type, model_name, property):
        ...
    
    def set_property(self, model_type, model_name, property, value):
        ...
        
    def add_object(self, model_type, model_name, properties):
        ...
    
    def get_results(self, params):
        settings = {}
        for k, v in params.items():
            settings[k] = {}
            ppties = params[k]["id_fields"]
            for p in ppties:
                settings[k][p] = True
        results = self.psse_obj.get_results(settings)
        return results
    
    
class PSSE_Model(om.ExplicitComponent, PSSE):
    def __init__(self, problem_file, settings_file_path, psse_path):
        super().read_problem_data(problem_file)
        self.case = self.load_model(settings_file_path, psse_path)
        return super().__init__()
        
    def setup(self, inputs, outputs):
        ...
        
    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")
        return
