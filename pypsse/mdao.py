import logging

import openmdao.api as om

from pypsse.simulator import Simulator

logger = logging.getLogger("model")


class PSSE:
    "The class defines the PSSE interface to OpenMDAO"
    model_loaded = False

    def load_model(self, settings_file_path, psse_path):
        "Load the PyPSSE model"
        self.psse_obj = Simulator(settings_file_path, psse_path)
        self.time_counter = 0
        self.psse_obj.init()
        self.model_loaded = True

    def solve_step(self):
        "Solves for the current time set and incremetn in time"
        self.current_result = self.psse_obj.step(self.time_counter)
        self.time_counter += self.psse_obj.settings["Simulation"]["Step resolution (sec)"]
        return self.current_result

    def export_result(self):
        "Updates results in the result container"
        if not self.psse_obj.export_settings["Export results using channels"]:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()

    def close_case(self):
        "Closes the loaded model in PyPSSE"
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f"PSSE case {self.uuid} closed.")

    def get_results(self, params):
        "Queries results from PyPSSE"
        settings = {}
        for k, _ in params.items():
            settings[k] = {}
            ppties = params[k]["id_fields"]
            for p in ppties:
                settings[k][p] = True
        results = self.psse_obj.get_results(settings)
        return results


class PSSEModel(om.ExplicitComponent, PSSE):
    "Expicit OpenMDAO component"

    def __init__(self, problem_file, settings_file_path, psse_path):
        "Initializes the optimization problem"
        super().read_problem_data(problem_file)
        self.case = self.load_model(settings_file_path, psse_path)
        super().__init__()

    def setup(self, *_, **__):
        "Sets up the optimization problem"
        ...

    def setup_partials(self):
        "Sets up the partial derivatives"
        self.declare_partials("*", "*", method="fd")
