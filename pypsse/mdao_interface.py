import logging

import openmdao.api as om
import numpy as np
import toml, json

from pypsse.simulator import Simulator
from pypsse.enumerations import WritableModelTypes
from pypsse.models import MdaoProblem

logger = logging.getLogger("model")


class PSSE:
    "The class defines the PSSE interface to OpenMDAO"
    model_loaded = False


    def load_model(self, settings_file_path):
        "Load the PyPSSE model"
        self.psse_obj = Simulator(settings_file_path)
        self.assets = self.psse_obj.raw_data 
        self.time_counter = 0
        self.psse_obj.init()
        self.model_loaded = True
        
    def _build_inputs(self):
        inputs = {}
        for input in self.probelm.inputs:
            self.psse_obj.sim.update_object(
                dtype=input.asset_type.value, 
                bus=input.asset_bus, 
                element_id=input.asset_id, 
                values=input.attributes
            )
            for var, val in input.attributes.items():
                tag = "{}_{}_{}_{}".format(
                    input.asset_type.value,
                    input.asset_id,
                    input.asset_bus,
                    var
                    )
                inputs[tag] = [val]
          
        self.solve_step()
        return inputs
    
    def _list_inputs(self):
        return list(self._psse_inputs.keys())
    
    def _build_outputs(self, output=None):
        outputs = json.loads(self.probelm.outputs.model_dump_json())   
        buses = outputs["buses"]
        quantities = outputs["quantities"]
        
        results = self.psse_obj.sim.read_subsystems(
            subsystem_buses = buses,
            quantities = quantities
        )
        if output is None:
            output= {}
        for obj_ppty, values in results.items():
            asset_type, asset_property =  obj_ppty.split("_")
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
        
        print('Buses_153_PU', output['Buses_153_PU'])
        
        return output
    
    def _update_inputs(self, inputs):
        attr_keys = {}
        for input in inputs:
            k, attr = input.rsplit("_",1)
            if k not in attr_keys:
                attr_keys[k] = {}
            attr_keys[k][attr] = inputs[input][0]
        
        for info, attrs in attr_keys.items():
            asset_type, asset_id, asset_bus_id = info.split("_")
            self.psse_obj.sim.update_object(
                dtype=asset_type, 
                bus=int(asset_bus_id), 
                element_id=asset_id, 
                values=attrs
            )
    
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
        
        
        #results = self.get_results()
        return #self.map_results(results)

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

    def update_ouputs(self, outputs, results):
        for output in outputs:
            result = np.array(results[output])
            outputs[output] = result


    def read_problem_data(self, problem_file):
        data = toml.load(problem_file)
        self.probelm = MdaoProblem(**data)


class PSSEModel(om.ExplicitComponent, PSSE):
    "Expicit OpenMDAO component"

    def __init__(self, settings_file_path, problem_file):
        "Initializes the optimization problem"
        self.read_problem_data(problem_file)
        self.case = self.load_model(settings_file_path)
        super().__init__()
        self._psse_inputs = self._build_inputs()
        for var, val in self._psse_inputs.items():
            #print("input", var, val)
            self.add_input(var, val=val)
        
        self._psse_outputs = self._build_outputs()
        for var, val in self._psse_outputs.items():
            #print("output", var, val)
            self.add_output(var, val=val)
        

    def setup(self):
        "Sets up the optimization problem"

    def setup_partials(self):
        "Sets up the problem partial derivatives"
        self.declare_partials("*", "*", method="fd")
        return

    def compute(self, inputs, outputs):
        "Sets up the compute method"
        self._psse_inputs = inputs
        self._psse_outputs = outputs
        self._update_inputs(inputs)
        self.solve_step()
        self._build_outputs(outputs)
        
    def __repr__(self):
        input_str = ''
        for input, val in self._psse_inputs.items():
            input_str += f" {input} - {val}\n"
            
        output_str = ''
        for output, val in self._psse_outputs.items():
            output_str += f" {output} - {val}\n"
        
        msg = f"""Inputs:\n{input_str}\nOutputs:\n{output_str}"""
        return msg 
