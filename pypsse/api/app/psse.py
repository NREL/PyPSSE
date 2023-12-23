# Standard imports
import json
import logging
from http import HTTPStatus
from inspect import signature
from multiprocessing import current_process
from queue import Empty

from pypsse.api.common import BASE_PROJECT_PATH
from pypsse.common import MAPPED_CLASS_NAMES, SIMULATION_SETTINGS_FILENAME
from pypsse.enumerations import ApiCommands, SimulationStatus
from pypsse.models import ApiAssetQuery, ApiPssePostRequest, ApiPsseReply, ApiWebSocketRequest
from pypsse.simulator import Simulator

logger = logging.getLogger(__name__)
# Make sure to change the PSSE path


class SimulatorUtils:
    def open_case(
        self,
        parameters,
    ):
        if isinstance(parameters, dict):
            parameters = ApiPssePostRequest(**parameters)

        """Run the case file."""

        project_path = BASE_PROJECT_PATH / parameters.project_name
        assert project_path.exists(), f"Project path {project_path!s} does not exist"
        simulation_filepath = project_path / SIMULATION_SETTINGS_FILENAME
        self.logger.info(SimulationStatus.STARTING_INSTANCE.value)
        self.psse_obj = Simulator(settings_toml_path=simulation_filepath)
        self.logger.info(SimulationStatus.INITIALIZATION_COMPLETE.value)
        self.time = self.psse_obj.settings.simulation.start_time
        return ""

    def close_case(self):
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f"PSSE case {self.uuid} closed.")

    def status(self):
        if self.psse_obj is None:
            return SimulationStatus.NOT_INITIALIZED.value
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
                results[asset_type] = list(asset_info)
        return results

    def query_all(self):
        results = self.results_by_ppty
        return results

    def query_by_asset(self, parameters):
        if isinstance(parameters, dict):
            parameters = ApiAssetQuery(**parameters)

        assert hasattr(parameters, "asset_type") and hasattr(
            parameters, "asset_id"
        ), "Reqired keys: asset_type, asset_id"
        inv_map = {v: k for k, v in MAPPED_CLASS_NAMES.items()}
        asset_type = inv_map[parameters.asset_type]
        return self.results_by_id[asset_type][parameters.asset_id]

    def query_by_ppty(self, parameters):
        if isinstance(parameters, dict):
            parameters = ApiAssetQuery(**parameters)

        assert hasattr(parameters, "asset_type") and hasattr(
            parameters, "asset_property"
        ), "Reqired keys: asset_type, asset_property"
        inv_map = {v: k for k, v in MAPPED_CLASS_NAMES.items()}
        asset_type = inv_map[parameters.asset_type]
        return self.results_by_ppty[asset_type][parameters.asset_property]

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

                if isinstance(value, complex):
                    val = [value.real, value.imag]
                elif isinstance(value, list):
                    val = []
                    for v in value:
                        val.append([v.real, v.imag])
                else:
                    val = value

                val_struct = {"value": val, "dtype": str(value.__class__.__name__)}

                self.results_by_id[new_asset_type][asset_id][asset_property] = val_struct
                self.results_by_ppty[new_asset_type][asset_property][asset_id] = val_struct


class SimulatorWebSocket(SimulatorUtils):
    def __init__(
        self,
        shutdown_event=None,
        to_psse_queue=None,
        from_psse_queue=None,
    ):
        super().__init__()
        self._validate_methods()
        self.uuid = current_process().name

        # Setting up logger for the process
        # qh = logging.handlers.QueueHandler(logging_queue)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        # self.logger.addHandler(qh)
        self.logger.info("%s - psse uuid init time", self.uuid)

        self.shutdownevent = shutdown_event
        self.to_psse_queue = to_psse_queue
        self.from_psse_queue = from_psse_queue

        # PyPSSE object responsible for communicating to PSSE API
        self.psse_obj = None
        self.time_counter = 0
        self.multipart, self.multipart_data = {}, {}
        # TODO: I don't know if we need to check at this point
        # whether we can import psse35 and psspy

        self._add_message_to_queue(
            ApiPsseReply(status=HTTPStatus.OK, message="sucessfully initialized.", uuid=self.uuid)
        )
        self.run()

    def _get_arguments(self, command_str: str):
        """Internal method to return list of arguments."""
        # Check if the command specified by the
        # user is defined as method in class
        if not hasattr(self, command_str):
            self._add_message_to_queue(
                ApiPsseReply(
                    status=HTTPStatus.BAD_REQUEST, message=f"Command {command_str} does not exist.", uuid=self.uuid
                )
            )
            return
        command = getattr(self, command_str)
        return command, list(signature(command).parameters)

    def _add_message_to_queue(self, model_instance: ApiPsseReply):
        # Enums are not JSON serializable
        # so need to first convert to json and load into pythin dict
        self.from_psse_queue.put(json.loads(model_instance.model_dump_json()))

    def _get_task(self):
        """Internal method to parse task."""

        task = self.to_psse_queue.get()

        try:
            if task == "END" or task is None:
                return task
            return ApiWebSocketRequest(**json.loads(task))  # json.loads(task)

        # pylint: disable=broad-exception-caught
        except Exception as err:
            msg = f"Error parsing the inputs as dictionary: {err!s} > input: {task}"
            self.logger.error(msg)
            self._add_message_to_queue(
                ApiPsseReply(status=HTTPStatus.INTERNAL_SERVER_ERROR, message=msg, uuid=self.uuid)
            )

    def run(self) -> None:
        """Runs indefinitey until shutdown by setting
        the event or END command is sent
        """

        self.logger.info("PSSE simulation starting")

        while not self.shutdownevent.is_set():
            try:
                # Fetch the task from queue break
                task = self._get_task()

                if task is None:
                    continue

                if task == "END":
                    break

                func, attrs = self._get_arguments(task.command)

                try:
                    if "parameters" in attrs:
                        command_return = func(parameters=task.parameters)
                    else:
                        command_return = func()

                    result = ApiPsseReply(status=HTTPStatus.OK, message=json.dumps(command_return), uuid=self.uuid)

                except Exception as e:
                    result = ApiPsseReply(status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e), uuid=self.uuid)
                self._add_message_to_queue(result)

            except Empty:
                continue

            except (KeyboardInterrupt, SystemExit):
                break

        self.logger.info("%s - finishing PSSE simulation", self.uuid)
        msg = "Closed PSSE instance"
        self._add_message_to_queue(ApiPsseReply(status=HTTPStatus.OK, message=msg, uuid=self.uuid))


class SimulatorAPI(SimulatorUtils):
    def __init__(
        self, shutdown_event=None, to_psse_queue=None, from_psse_queue=None, params: ApiPssePostRequest = None
    ):
        super().__init__()

        self._validate_methods()

        self.uuid = current_process().name
        logger.info(f"{self.uuid} - psse uuid init time")
        self.shutdownevent = shutdown_event
        self.to_psse_queue = to_psse_queue
        self.from_psse_queue = from_psse_queue

        project_path = BASE_PROJECT_PATH / params.project_name
        assert project_path.exists(), f"Project path {project_path!s} does not exist"
        simulation_filepath = project_path / SIMULATION_SETTINGS_FILENAME
        try:
            self.psse_obj = Simulator(settings_toml_path=simulation_filepath)
            logger.info(f"{self.uuid} - psse dispatched")
            result = ApiPsseReply(
                status=HTTPStatus.OK, message=f"Simulation {self.uuid} successfully initiallized.", uuid=self.uuid
            )
            if from_psse_queue is not None:
                self.from_psse_queue.put(result)
            self.time = self.psse_obj.settings.simulation.start_time
            self.run()
        except Exception as e:
            result = ApiPsseReply(status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e), uuid=self.uuid)
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
                        self.from_psse_queue.put(ApiPsseReply(status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e)))

                    command_name = task.pop("command")

                    if hasattr(self, command_name):
                        command = getattr(self, command_name)
                        try:
                            if "parameters" in list(signature(command).parameters):
                                command_return = command(parameters=task["parameters"])
                            else:
                                command_return = command()
                            print("command_return: ", command_return)
                            result = ApiPsseReply(status=HTTPStatus.OK, message=json.dumps(command_return))
                            print("ApiPsseReply: ", result)
                        except Exception as e:
                            result = ApiPsseReply(status=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e))

                    else:
                        result = ApiPsseReply(
                            status=HTTPStatus.UNPROCESSABLE_ENTITY, message=f"Command {command_name} does not exist."
                        )

                self.from_psse_queue.put(result)
            except Empty:
                continue
            except (KeyboardInterrupt, SystemExit):
                break
        msg = f"{self.uuid} - finishing simulation"
        logger.info(msg)
        result = ApiPsseReply(status=HTTPStatus.OK, message=msg)
        logger.info(msg)
        self.from_psse_queue.put(result)
