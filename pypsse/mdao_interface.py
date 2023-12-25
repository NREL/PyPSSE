import json

import numpy as np
import openmdao.api as om
import toml
from loguru import logger

from pypsse.models import MdaoProblem, SimulationSettings
from pypsse.simulator import Simulator


class PSSE:
    "The class defines the PSSE interface to OpenMDAO"
    model_loaded = False

    def load_model(self, settings_file_path):
        "Load the PyPSSE model"
        settings = toml.load(settings_file_path)
        settings["simulation"]["project_path"] = settings_file_path.parent
        settings = SimulationSettings(**settings)
        self.psse_obj = Simulator(settings)
        self.assets = self.psse_obj.raw_data
        self.time_counter = 0
        self.psse_obj.init()
        self.model_loaded = True

    def _build_inputs(self):
        inputs_dict = {}
        for input_model in self.probelm.inputs:
            self.psse_obj.sim.update_object(
                dtype=input_model.asset_type.value,
                bus=input_model.asset_bus,
                element_id=input_model.asset_id,
                values=input_model.attributes,
            )
            for var, val in input_model.attributes.items():
                tag = f"{input_model.asset_type.value}_{input_model.asset_id}_{input_model.asset_bus}_{var}"
                inputs_dict[tag] = [val]
        logger.info("MDAO inputs built sucessfully")
        self.solve_step()
        return inputs_dict

    def _list_inputs(self):
        return list(self._psse_inputs.keys())

    def _build_outputs(self, output=None):
        outputs = json.loads(self.probelm.outputs.model_dump_json())
        buses = outputs["buses"]
        quantities = outputs["quantities"]

        results = self.psse_obj.sim.read_subsystems(subsystem_buses=buses, quantities=quantities)
        if output is None:
            output = {}
        for obj_ppty, values in results.items():
            asset_type, asset_property = obj_ppty.split("_")
            for obj_id, value in values.items():
                if isinstance(obj_id, int):
                    bus_id = obj_id
                    object_id = None
                else:
                    obj_id = obj_id.replace(" ", "")
                    bus_id, object_id = obj_ppty.split("_")
                if object_id:
                    tag = f"{asset_type}_{object_id}_{bus_id}_{asset_property}"
                else:
                    tag = f"{asset_type}_{bus_id}_{asset_property}"

                if isinstance(value, complex):
                    output[f"{tag}_real"] = [value.real]
                    output[f"{tag}_imag"] = [value.imag]
                else:
                    output[f"{tag}"] = [value]
        logger.info("MDAO outputs built sucessfully")
        return output

    def _update_inputs(self, inputs):
        attr_keys = {}
        for _input in inputs:
            k, attr = _input.rsplit("_", 1)
            if k not in attr_keys:
                attr_keys[k] = {}
            attr_keys[k][attr] = inputs[_input][0]

        for info, attrs in attr_keys.items():
            asset_type, asset_id, asset_bus_id = info.split("_")
            self.psse_obj.sim.update_object(dtype=asset_type, bus=int(asset_bus_id), element_id=asset_id, values=attrs)
        logger.info("MDAO inputs updated sucessfully")

    def models_to_dict(self, models):
        mdl = {}
        for bus, load_id in models:
            if bus not in mdl:
                mdl[bus] = []
            mdl[bus].append(load_id)
        return mdl

    def solve_step(self):
        "Solves for the current time set and incremetn in time"
        self.psse_obj.inc_time = False
        self.current_result = self.psse_obj.step(self.time_counter)

    def export_result(self):
        "Updates results in the result container"
        if not self.psse_obj.export_settings.export_results_using_channels:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()
        logger.info("Result sucessfully exported")

    def close_case(self):
        "Closes the loaded model in PyPSSE"
        self.psse_obj.psse.pssehalt_2()
        del self.psse_obj
        logger.info("PSSE case closed.")

    def update_ouputs(self, outputs, results):
        for output in outputs:
            result = np.array(results[output])
            outputs[output] = result
        logger.info("MDAO outputs updates.")

    def read_problem_data(self, problem_file):
        data = toml.load(problem_file)
        self.probelm = MdaoProblem(**data)
        logger.info("MDAO probelm parameters read. Building inputs and outputs.")

    def __del__(self):
        self.export_result()
        self.close_case()


class PSSEModel(om.ExplicitComponent, PSSE):
    "Expicit OpenMDAO component"

    def __init__(self, settings_file_path, problem_file):
        "Initializes the optimization problem"
        self.read_problem_data(problem_file)
        self.case = self.load_model(settings_file_path)
        super().__init__()
        self._psse_inputs = self._build_inputs()
        for var, val in self._psse_inputs.items():
            self.add_input(var, val=val)

        self._psse_outputs = self._build_outputs()
        for var, val in self._psse_outputs.items():
            self.add_output(var, val=val)

    def setup(self):
        "Sets up the optimization problem"

    def setup_partials(self):
        "Sets up the problem partial derivatives"
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        "Sets up the compute method"
        self._psse_inputs = inputs
        self._psse_outputs = outputs
        self._update_inputs(inputs)
        self.solve_step()
        self._build_outputs(outputs)

    def __repr__(self):
        input_str = ""
        for _input, val in self._psse_inputs.items():
            input_str += f" {_input} - {val}\n"

        output_str = ""
        for output, val in self._psse_outputs.items():
            output_str += f" {output} - {val}\n"

        msg = f"""Inputs:\n{input_str}\nOutputs:\n{output_str}"""
        return msg
