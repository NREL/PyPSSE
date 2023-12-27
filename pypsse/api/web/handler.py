import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from multiprocessing import Event, Process, Queue, cpu_count
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from pydantic import UUID4

from pypsse.api.app.psse import SimulatorAPI, SimulatorWebSocket
from pypsse.api.common import BASE_PROJECT_PATH
from pypsse.common import DEFAULT_LOG_FILE, DEFAULT_RESULTS_FILENAME, EXPORTS_FOLDER, LOGS_FOLDER
from pypsse.models import ApiPsseException, ApiPssePostRequest, ApiPssePutRequest, ApiPsseReply, ApiPsseReplyInstances

logger = logging.getLogger(__name__)

shutdown_event = Event()


class Handler:

    """Handlers for web server."""

    uuid_to_project_mapping = {}

    def __init__(self):
        """Constructor for PSSE handler."""

        logger.info("Initializing service handler")

        # Initializing dictionary for stroing psse_instances
        self.psse_instances = {}

        # Event flag to control shutdown of background tasks
        self.shutdown_event = Event()

        # Pool and Loop are used to catch returning Multiprocessing Queue messages
        #  to prevent blocking of the API.

        self.pool = ThreadPoolExecutor(max_workers=cpu_count() - 1)
        self.loop = asyncio.get_event_loop()
        self.router = APIRouter()
        self.router.add_websocket_route("/ws", self.handle_psse_websocket)
        self.router.add_api_route("/", self.post_psse, methods=["POST"])
        self.router.add_api_route("/", self.put_psse, methods=["PUT"])
        self.router.add_api_route("/uuid/{uuid}", self.delete_psse, methods=["DELETE"])
        self.router.add_api_route("/uuids", self.get_instance_uuids, methods=["GET"])
        self.router.add_api_route("/status/uuid/{uuid}", self.get_instance_status, methods=["GET"])
        self.router.add_api_route("/results/uuid/{uuid}", self.get_download_results, methods=["GET"])
        self.router.add_api_route("/log/uuid/{uuid}", self.get_download_logs, methods=["GET"])

    async def handle_psse_websocket(self, websocket: WebSocket):
        """Function to handle PSSE websocket."

        Args:
            websocket (WebSocket): web socket object
        """

        to_psse_queue, from_psse_queue = Queue(), Queue()
        psse_uuid = str(uuid4())

        p = Process(
            target=SimulatorWebSocket,
            name=psse_uuid,
            args=(
                shutdown_event,
                to_psse_queue,
                from_psse_queue,
            ),
        )
        p.start()

        logger.info("Starting websocket communication for %s", psse_uuid)

        await websocket.accept()
        result = from_psse_queue.get()
        await websocket.send_json(result)

        while True:
            data = await websocket.receive_text()
            logger.info("websocket message data: %s", str(result)[1:1000])
            to_psse_queue.put(data)
            result = from_psse_queue.get()
            logger.info("psse handler output = %s", str(result)[1:1000])
            await websocket.send_json(result)

            if data == "END":
                await websocket.close()
                break

    async def post_psse(self, request: ApiPssePostRequest) -> ApiPsseReply:
        """Create UUID and intialize and push to queue

        Args:
            request (ApiPssePostRequest): request for the server

        Returns:
            ApiPsseReply: returns response from the server
        """

        psse_uuid = str(uuid4())
        self.uuid_to_project_mapping[psse_uuid] = request.project_name
        to_psse_queue = Queue()
        from_psse_queue = Queue()

        # Create a process for launching PSSE instance
        p = Process(
            target=SimulatorAPI, name=psse_uuid, args=(self.shutdown_event, to_psse_queue, from_psse_queue, request)
        )

        # Store queue and process
        self.psse_instances[psse_uuid] = {
            "to_psse_queue": to_psse_queue,
            "from_psse_queue": from_psse_queue,
            "process": p,
        }

        # Catching data coming from PSSE
        psse_t = self.loop.run_in_executor(self.pool, self._post_put_background_task, psse_uuid)
        psse_t.add_done_callback(self._post_put_callback)

        # Start process for psse
        try:
            p.start()

            # Return a message to webclient
            return ApiPsseReply(
                status=HTTPStatus.OK,
                message="Starting PSSE",
                uuid=psse_uuid,
            )
        except Exception as e:
            self._base_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e), psse_uuid)

    async def put_psse(self, request: ApiPssePutRequest) -> ApiPsseReply:
        """Method for simulator put requst

        Args:
            request (ApiPssePutRequest): request object for the server

        Returns:
            ApiPsseReply: response from the server
        """
        logger.info(f"Running command :{request.model_dump_json()}")
        self._error_invalid_uuid(request.uuid)
        if not hasattr(request, "command") or not hasattr(request, "parameters"):
            self._base_error(HTTPStatus.NOT_FOUND, "Please provide a command and parameters", request.uuid)

        # psse_t = self.loop.run_in_executor(self.pool, self._post_put_background_task, request.uuid)
        # psse_t.add_done_callback(self._post_put_callback)

        logger.info(f"Submitted data to psse :{request.model_dump_json()}")
        self.psse_instances[str(request.uuid)]["to_psse_queue"].put(request.model_dump_json())
        results = self.psse_instances[str(request.uuid)]["from_psse_queue"].get()

        return ApiPsseReply(status="", message=f"{results}", uuid=request.uuid)

    async def delete_psse(self, uuid: UUID4) -> ApiPsseReply:
        """Delete an instance of simulation

        Args:
            uuid (UUID4): simulation instance uuid

        Returns:
            ApiPsseReply: response from the server
        """
        """Delete an instance of simulation"""
        self._error_invalid_uuid(uuid)
        try:
            psse_t = self.loop.run_in_executor(self.pool, self._delete_background_task, uuid)
            psse_t.add_done_callback(self._delete_callback)
            self.psse_instances[str(uuid)]["to_psse_queue"].put("END")
            self.psse_instances.pop(str(uuid))
            self.uuid_to_project_mapping.pop(str(uuid))
            return ApiPsseReply(status="", message="Attempting to close PyPSSE instance", uuid=uuid)
        except Exception:
            msg = f"Error closing in PSSE instance {uuid}"
            logger.error(msg)
            self._base_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error closing in PyPSSE instance", uuid)

    async def get_instance_uuids(self) -> ApiPsseReplyInstances:
        """get all running simulation uuids

        Returns:
            ApiPsseReplyInstances: server response
        """

        uuids = [str(k) for k in self.psse_instances.keys()]
        return ApiPsseReplyInstances(status=HTTPStatus.OK, message=f"{len(uuids)} uuids found", simulators=uuids)

    async def get_instance_status(self, uuid: UUID4) -> ApiPsseReplyInstances:
        """get status of the current provided simuation instance

        Args:
            uuid (UUID4): simulation instance UUID

        Returns:
            ApiPsseReplyInstances: server response
        """

        self._error_invalid_uuid(uuid)
        return ApiPsseReplyInstances(
            status=HTTPStatus.OK,
            message="UUID exists",
            uuid=str(uuid),
        )

    async def get_download_results(self, uuid: UUID4) -> FileResponse:
        """download results from a simulation instance

        Args:
            uuid (UUID4): simulation instance UUID

        Returns:
            FileResponse: hdf5 simulation results
        """

        self._error_invalid_uuid(uuid)

        project_name = self.uuid_to_project_mapping[str(uuid)]
        results_file = BASE_PROJECT_PATH / project_name / EXPORTS_FOLDER / DEFAULT_RESULTS_FILENAME
        if not results_file.exists():
            self._base_error(HTTPStatus.NOT_FOUND, "File not found", uuid)

        return FileResponse(path=results_file, filename=DEFAULT_RESULTS_FILENAME, media_type="hdf5")

    async def get_download_logs(self, uuid: UUID4) -> FileResponse:
        """download logs from a simulation instance

        Args:
            uuid (UUID4): simlation instance UUID

        Returns:
            FileResponse: returns simulation log files
        """

        if str(uuid) not in self.psse_instances.keys():
            param = "UUID={psse_uuid} not found in the PSSE instances"
            logger.error(f"{param}")
            self._base_error(HTTPStatus.NOT_FOUND, param, uuid)

        project_name = self.uuid_to_project_mapping[str(uuid)]
        results_file = BASE_PROJECT_PATH / project_name / LOGS_FOLDER / DEFAULT_LOG_FILE
        if not results_file.exists():
            self._base_error(HTTPStatus.NOT_FOUND, f"File not found - {results_file}", uuid)

        return FileResponse(path=results_file, filename=DEFAULT_LOG_FILE, media_type="hdf5")

    def _post_put_background_task(self, psse_uuid: UUID4) -> Any:
        """background task to retrieve results from simulation queue

        Args:
            psse_uuid (UUID4): simulation instance UUID

        Returns:
            Any: data types returned from the server
        """
        q = self.psse_instances[psse_uuid]["from_psse_queue"]
        ans = q.get()
        return ans

    def _post_put_callback(self, return_value):
        logger.info(f"{return_value.result()}")

    def _get_uuid(self, data: Any) -> UUID4:
        """returns simulation UUID

        Args:
            data (Any): pypsse objects

        Returns:
            UUID4: simulation UUID returned
        """

        if not hasattr(data, "uuid"):
            return None

        psse_uuid = data.uuid
        if psse_uuid not in self.psse_instances.keys():
            return None

        return psse_uuid

    def _delete_background_task(self, psse_uuid: UUID4) -> dict:
        """_summary_

        Args:
            psse_uuid (UUID4): simuation instance UUID

        Returns:
            dict: method response
        """
        while self.psse_instances[psse_uuid]["process"].is_alive():
            continue

        del self.psse_instances[psse_uuid]

        return {"Status": "Success", "Message": "PSSE instance closed", "UUID": psse_uuid}

    def _delete_callback(self, return_value):
        logger.info(f"{return_value.result()}")

    def _error_invalid_uuid(self, uuid: UUID4):
        if not uuid or str(uuid) not in self.psse_instances:
            self._base_error(HTTPStatus.NOT_FOUND, "UUID does not exist", uuid)

    def _base_error(self, status_code: HTTPStatus, message: str, uuid: UUID4):
        """_summary_

        Args:
            status_code (HTTPStatus): simulation status
            message (str): message from simulator
            uuid (UUID4): simulation instance UUID

        Raises:
            HTTPException: _description_
        """
        raise HTTPException(
            status_code=status_code,
            detail=ApiPsseException(
                message=message,
                uuid=uuid,
            ).model_dump_json(),
        )
