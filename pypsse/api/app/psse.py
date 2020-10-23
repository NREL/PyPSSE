# Standard imports
from pypsse.pyPSSE_instance import pyPSSE_instance
from multiprocessing import current_process
from aiohttp import web, WSMsgType
from queue import Empty
import logging
import inspect
import json
import yaml
import sys
import os

logger = logging.getLogger(__name__)
# Make sure to change the PSSE path 
PSSE_PATH = r"C:\Program Files (x86)\PTI\PSSE34\PSSPY37"

class PSSE:
    def __init__(self, shutdown_event=None, to_psse_queue=None, from_psse_queue=None, params=None):
        super().__init__()
        self.uuid = current_process().name
        logger.info(f"{self.uuid} - psse uuid init time")
        self.shutdownevent = shutdown_event
        self.to_psse_queue = to_psse_queue
        self.from_psse_queue = from_psse_queue
        self.psse_obj = pyPSSE_instance(settinigs_toml_path=params["filename"])
        if self.psse_obj.initSucess:
            logger.info("{} - psse dispatched".format(self.uuid))
            result = {
                "Status": "Success",
                "Message": "PSSE {} successfully initiallized.".format(self.uuid),
                "UUID": self.uuid
            }
            if from_psse_queue !=None: self.from_psse_queue.put(result)
            self.run()
        else:
            msg = f"Error launching PSSE"
            logger.error(msg)
    
    def run(self):
        logger.info("{} - PSSE simulation starting")
        while not self.shutdownevent.is_set():
            try:
                task = self.to_psse_queue.get()
                if task == 'END':
                    break
                else:
                    try:
                        task = json.loads(task)
                    except Exception as e:
                        msg = f"Error parsing the inputs as dictionary: " \
                            f"{str(e)} > input: {task}"
                        result = {"Status": "Failed", "Message": msg}
                        logger.error(msg)
                        self.from_psse_queue.put(result)
                        continue
                    if "command" not in task:
                        result = {"Status": "Failed",
                                  "Message": f"Valid command not provided"}
                    elif "parameters" not in task:
                        result = {"Status": "Failed",
                                  "Message": f"Valid parameters not provided"}
                    else:
                        command = task["command"]
                        parameters = task["parameters"]
                        if hasattr(self,command):
                            args = inspect.getfullargspec(eval("self.{}".format(command)))[0][1:]
                            if set(args).issubset(parameters.keys()):
                                command_str = ''
                                for arg in args:
                                    parameter = parameters[arg]
                                    if isinstance(parameter,str):
                                        parameter="r\"{}\"".format(parameter)
                                    command_str += f"{arg}={parameter},"
                                command_str = f"self.{command}({command_str[:-1]})"
                                command_return = eval(command_str)
                                result = {"Status":"Success","Data":command_return}
                            else:
                                result = {"Status":"Failed","Message":f"Wrong arguments passed to {command}"}
                        else:
                            result = {"Status":"Failed","Message":f"Command {command} does not exist."}
                self.from_psse_queue.put(result)
            except Empty:
                continue
            except (KeyboardInterrupt, SystemExit):
                break
        logger.info(f"{self.uuid} - finishing PSSE simulation")
        msg = f'Closed PSSE instance'
        result = {"Status": "Success", "Message": msg, "UUID": self.uuid}
        logger.info(msg)
        self.from_psse_queue.put(result)

    def init(self):
        self.time_counter = 0
        self.psse_obj.init()
        self.psse_obj.initialize_loads()

    def update_settings(self, new_dict: dict):
        for key, value in new_dict.items():
            if key in self.psse_obj.settings:
                self.psse_obj.settings[key].update(value)
            else:
                logger.warning(f"{key} not present in settings.toml file")

    def get_results(self, params):
        # print("\n\nGetting results\n\n")
        # params = {
        #     "Loads": {
        #         "id_fields": ["MVA"]
        #     },
        #     "Buses": {
        #         "id_fields": ["PU", "ANGLE"]
        #     },
        # }
        settings = {}
        for k, v in params.items():
            settings[k] = {}
            ppties = params[k]["id_fields"]
            for p in ppties:
                settings[k][p] = True
        results = self.psse_obj.get_results(settings)
        # TODO: KAPIL you will return the results
        return results




    def solve_step(self):
        self.current_result = self.psse_obj.step(self.time_counter)
        self.time_counter += self.psse_obj.settings['Simulation']["Step resolution (sec)"]
        return self.current_result

    def export_result(self):
        self.psse_obj.PSSE.pssehalt_2()
        if not self.psse_obj.export_settings["Export results using channels"]:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()
    
    def ingest_subscription(self, key_obj: dict, bes_asset_id: list, value):
        if key_obj['asset_type'] == 'bus':
            if key_obj['parameter_name'] == "power_real":
                self.psse_obj.load_chng_5(ibus = bes_asset_id[0], id= bes_asset_id[1],
                realar1=value)
            if key_obj['parameter_name'] == "power_imag":
                self.psse_obj.load_chng_5(ibus = bes_asset_id[0], id= bes_asset_id[1],
                realar2=value)

    def query_param(self, key_obj: dict ={}):
        rval = False
        if  key_obj['asset_type'] == 'bus':
            if  key_obj['parameter_name'] == 'voltage' and key_obj['parameter_unit'] == 'pu':
                rval = self.current_result['Buses_PU'].get(key_obj['asset_name'])
            elif key_obj['parameter_name'] == 'voltage_angle' and key_obj['parameter_unit'] == 'deg':
                rval = self.current_result['Buses_ANGLED'].get(key_obj['asset_name'])
            if key_obj['parameter_name'] == 'power_mismatch' and key_obj['parameter_unit'] == 'mw':
                rval = self.current_result['Buses_MISMATCH'].get(key_obj['asset_name'])
        logger.info(f"Query return value is {rval} for {key_obj['parameter_name']}")
        if rval is None:
            return False
        else:
            return rval

    def close_case(self):
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f'PSSE case {self.uuid} closed.')

    # def inject_contingency(self,contingency_data):
    #     """
    #     function to inject contingencies into PyPSSE object.
    #     """
    #     for k in contingency_data.keys():
    #         globals()[k]= contingency_data[k]
    #     # print("INJECT CONTINGENCY {}",fault_type,  flush=True)
    #     if (fault_type == "line_fault"):
    #         data_struct = {'contingencies': {fault_type: {
    #             asset_name: {"time": time, asset_type: asset_ids, "duration": duration,
    #                          "fault_impedance": fault_impedance}}}}
    #     elif (fault_type == "line_trip"):
    #         data_struct = {'contingencies': {fault_type: {
    #             asset_name: {"time": time, asset_type: asset_ids}}}}
    #
    #     elif (fault_type == "bus_trip"):
    #         data_struct = {'contingencies': {fault_type: {
    #             asset_name: {"time": time, asset_type: asset_ids}}}}
    #
    #     elif (fault_type == "bus_fault"):
    #         data_struct = {'contingencies': {fault_type: {
    #             asset_name: {"time": time, asset_type: asset_ids, "duration": duration,
    #                          "fault_impedance": fault_impedance, "bus_trip" : bus_trip, "trip_delay" : trip_delay}}}}
    #     elif (fault_type == "machine_trip"):
    #         data_struct = {'contingencies': {fault_type: {
    #             asset_name: {"time": time, asset_type: asset_ids, "machine_id": machine_id}}}}
    #     # print(" inject data : {} ".format(data_struct))
    #     try:
    #         self.psse_obj.inject_contingencies_external(data_struct)
    #     except Exception as e:
    #         print("Exception as ",e, flush=True)

if __name__ == '__main__':

    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.basicConfig(level=logger.INFO, format=FORMAT)

    a = PSSE()
    del a
