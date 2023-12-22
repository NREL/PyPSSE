# Standard imports
from inspect import signature
import json
import logging

from multiprocessing import current_process
from queue import Empty

from pypsse.simulator import Simulator
from pypsse.models import ApiPssePostRequest, ApiPsseReply
from pypsse.enumerations import ApiCommands
from pypsse.api.common import BASE_PROJECT_PATH
from pypsse.common import SIMULATION_SETTINGS_FILENAME, MAPPED_CLASS_NAMES

from http import HTTPStatus

logger = logging.getLogger(__name__)
# Make sure to change the PSSE path

class PSSE:
    
    def __init__(self, shutdown_event=None, to_psse_queue=None, from_psse_queue=None, params:ApiPssePostRequest=None):
        super().__init__()
        
        self._validate_methods()
    
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

                    if hasattr(self, command_name):
                        command = getattr(self, command_name)
                        try:
                            if "parameters" in list(signature(command).parameters):
                                command_return = command(parameters=task["parameters"])
                            else:
                                command_return = command()
                            print(command_name, command_return)
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
                                message= f"Command {command_name} does not exist."
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

    def close_case(self):
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f"PSSE case {self.uuid} closed.")
    
    def status(self):
        print(self.psse_obj._status)
        return self.psse_obj._status
     
    def run_simulation(self):
        self.psse_obj.run()

    def run_step(self):
        t = (self.time - self.psse_obj.settings.simulation.start_time).total_seconds()
        self.current_result = self.psse_obj.step(t)
        self.time += self.psse_obj.settings.simulation.simulation_step_resolution
        self._restructure_results()
        return self.psse_obj._status
    
    def export_result(self):
        self.psse_obj.PSSE.pssehalt_2()
        if not self.psse_obj.export_settings.export_results_using_channels:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()

    def update_model(self, parameters):
        ...
    
    def update_settings(self, parameters):
        for key, value in parameters.items():
            if key in self.psse_obj.settings:
                self.psse_obj.settings[key].update(value)
            else:
                logger.warning(f"{key} not present in settings.toml file")

    def query_asset_list(self):
        results = {}
        for asset_type, asset_info in self.results_by_id.items():
            if asset_type not in results:
                results[asset_type] = [asset_id for asset_id in asset_info]
        return results
        
    def query_all(self):
        results = self.results_by_ppty
        return results
    
    def query_by_asset(self, parameters ):
        assert 'asset_type' in parameters and 'asset_id' in parameters,'Reqired keys: asset_type, asset_id'
        inv_map = {v: k for k, v in MAPPED_CLASS_NAMES.items()}
        asset_id = parameters['asset_id']
        asset_type = inv_map[parameters['asset_type']] 
        return self.results_by_id[asset_type][asset_id]
        
    def query_by_ppty(self, parameters):
        assert 'asset_type' in parameters and 'asset_property' in parameters,'Reqired keys: asset_type, asset_property'
        inv_map = {v: k for k, v in MAPPED_CLASS_NAMES.items()}
        asset_type = inv_map[parameters['asset_type']] 
        asset_property = parameters['asset_property']
        return self.results_by_ppty[asset_type][asset_property]

    def _validate_methods(self):
        for command in ApiCommands:
            assert hasattr(self, command.value)

    def _restructure_results(self):
        inv_map = {v: k for k, v in MAPPED_CLASS_NAMES.items()}
        self.results_by_id = {}
        self.results_by_ppty = {}
        for info, val_dict in self.current_result.items():
            asset_type, asset_property = info.split("_")
            new_asset_type = inv_map[asset_type]      
            for asset_id, value in val_dict.items():
                if new_asset_type not in self.results_by_id:
                    self.results_by_id[new_asset_type] = {}
                    self.results_by_ppty[new_asset_type] = {}
                if asset_id not in self.results_by_id[new_asset_type]:
                    self.results_by_id[new_asset_type][asset_id] = {}
                if asset_property not in self.results_by_ppty[new_asset_type]:
                    self.results_by_ppty[new_asset_type][asset_property] = {}
                
                self.results_by_id[new_asset_type][asset_id][asset_property] = value
                self.results_by_ppty[new_asset_type][asset_property][asset_id] = value
        return 