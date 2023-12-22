# Standard imports
from inspect import signature
import json
import logging

from multiprocessing import current_process
from queue import Empty

from pypsse.modes.constants import dyn_only_options
from pypsse.simulator import Simulator
from pypsse.models import ApiPssePostRequest, ApiPsseReply
from pypsse.api.common import BASE_PROJECT_PATH
from pypsse.common import SIMULATION_SETTINGS_FILENAME

from http import HTTPStatus

logger = logging.getLogger(__name__)
# Make sure to change the PSSE path

class PSSE:
    def __init__(self, shutdown_event=None, to_psse_queue=None, from_psse_queue=None, params:ApiPssePostRequest=None):
        super().__init__()
        self.uuid = current_process().name
        logger.info(f"{self.uuid} - psse uuid init time")
        self.shutdownevent = shutdown_event
        self.to_psse_queue = to_psse_queue
        self.from_psse_queue = from_psse_queue

        project_path = BASE_PROJECT_PATH / params.project_name
        assert project_path.exists(), f"Project path {str(project_path)} does not exist"
        simulation_filepath = project_path / SIMULATION_SETTINGS_FILENAME
        try:
            self.psse_obj = Simulator(settings_toml_path=simulation_filepath)
            logger.info(f"{self.uuid} - psse dispatched")
            result = ApiPsseReply(
                status=HTTPStatus.OK,
                message=f"Simulation {self.uuid} successfully initiallized.",
                uuid=self.uuid
            )
            if from_psse_queue is not None:
                self.from_psse_queue.put(result)
            self.time = self.psse_obj.settings.simulation.start_time
            self.run()
        except Exception as e:
            result = ApiPsseReply(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                message=str(e),
                uuid=self.uuid
            )
        else:
            logger.error(result.model_dump_json())

    def run(self):
        logger.info("{} - Simulation starting")
        while not self.shutdownevent.is_set():
            try:
                task = self.to_psse_queue.get()
                if task == "END":
                    break
                else:
                    try:
                        task = json.loads(task)
                    except Exception as e:
                        logger.error(str(e))
                        self.from_psse_queue.put(
                            ApiPsseReply(
                                status = HTTPStatus.INTERNAL_SERVER_ERROR,
                                message=str(e)
                            )
                        )

                    command_name = task.pop("command")
                    print(command_name)
                    if hasattr(self, command_name):
                        command = getattr(self, command_name)
        
                        
                        try:
                            if "parameters" in list(signature(command).parameters):
                                print("Has parameters")
                                command_return = command(parameters=task["parameters"])
                            else:
                                print("Has no parameters")
                                command_return = command()
                            
                            result = ApiPsseReply(
                                status = HTTPStatus.OK,
                                message= command_return
                            )
                        except Exception as e:
                            result = ApiPsseReply(
                                status = HTTPStatus.INTERNAL_SERVER_ERROR,
                                message= str(e)
                            )
            
                    else:
                        result = ApiPsseReply(
                                status = HTTPStatus.UNPROCESSABLE_ENTITY,
                                message= f"Command {command_str} does not exist."
                            )
                         
                self.from_psse_queue.put(result)
            except Empty:
                continue
            except (KeyboardInterrupt, SystemExit):
                break
        msg = f"{self.uuid} - finishing simulation"
        logger.info(msg)
        result = ApiPsseReply(
            status = HTTPStatus.OK,
            message= msg
        )
        logger.info(msg)
        self.from_psse_queue.put(result)

    def update_settings(self, new_dict: dict):
        for key, value in new_dict.items():
            if key in self.psse_obj.settings:
                self.psse_obj.settings[key].update(value)
            else:
                logger.warning(f"{key} not present in settings.toml file")

    def get_results(self, parameters):
        print("RESULTING")
        results = self.psse_obj.get_results(parameters)
        print(results)
        return results

    def run_simulation(self):
        self.psse_obj.run()

    def run_step(self):
        print("RUNNING STEP")
        t = (self.time - self.psse_obj.settings.simulation.start_time).total_seconds()
        self.current_result = self.psse_obj.step(t)
        self.time += self.psse_obj.settings.simulation.simulation_step_resolution
        return self.current_result

    def export_result(self):
        self.psse_obj.PSSE.pssehalt_2()
        if not self.psse_obj.export_settings.export_results_using_channels:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()

    def ingest_subscription(self, key_obj: dict, bes_asset_id: list, value):
        if key_obj["asset_type"] == "bus":
            if key_obj["parameter_name"] == "power_real":
                self.psse_obj.load_chng_5(ibus=bes_asset_id[0], id=bes_asset_id[1], realar1=value)
            if key_obj["parameter_name"] == "power_imag":
                self.psse_obj.load_chng_5(ibus=bes_asset_id[0], id=bes_asset_id[1], realar2=value)

    def query_param(self, key_obj=None):
        if key_obj is None:
            key_obj = {}

        rval = False
        if key_obj["asset_type"] == "bus":
            if key_obj["parameter_name"] == "voltage" and key_obj["parameter_unit"] == "pu":
                rval = self.current_result["Buses_PU"].get(key_obj["asset_name"])
            elif key_obj["parameter_name"] == "voltage_angle" and key_obj["parameter_unit"] == "deg":
                rval = self.current_result["Buses_ANGLED"].get(key_obj["asset_name"])
            if key_obj["parameter_name"] == "power_mismatch" and key_obj["parameter_unit"] == "mw":
                rval = self.current_result["Buses_MISMATCH"].get(key_obj["asset_name"])
        logger.info(f"Query return value is {rval} for {key_obj['parameter_name']}")
        if rval is None:
            return False
        else:
            return rval

    def close_case(self):
        print("CLOSING")
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f"PSSE case {self.uuid} closed.")