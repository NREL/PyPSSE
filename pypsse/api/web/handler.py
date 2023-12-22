import asyncio

import logging
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Event, Process, Queue, cpu_count
from uuid import uuid4

from pydantic import UUID4

from pypsse.models import ApiPsseReply, ApiPsseReplyInstances, ApiPssePutRequest, ApiPssePostRequest, ApiPsseException
from pypsse.api.app.psse import PSSE

from fastapi import APIRouter

from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

from pypsse.common import DEFAULT_RESULTS_FILENAME, LOGS_FOLDER, DEFAULT_LOG_FILE, EXPORTS_FOLDER
from pypsse.api.common import BASE_PROJECT_PATH

from http import HTTPStatus

logger = logging.getLogger(__name__)


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
        self.router.add_api_route("/psse", self.get_psse, methods=["GET"])
        self.router.add_api_route("/psse", self.post_psse, methods=["POST"])
        self.router.add_api_route("/psse", self.put_psse, methods=["PUT"])
        self.router.add_api_route("/psse/uuid/{uuid}", self.delete_psse, methods=["DELETE"])
        self.router.add_api_route("/get_instance_uuids", self.get_instance_uuids, methods=["GET"])
        self.router.add_api_route("/psse/status/uuid/{uuid}", self.get_instance_status, methods=["GET"])
        self.router.add_api_route("/psse/download_results/uuid/{uuid}", self.get_download_results, methods=["GET"])
        self.router.add_api_route("/psse/download_log/uuid/{uuid}", self.get_download_logs, methods=["GET"])
        
    async def get_psse(self, request):
        """Websocket handler for psse instance"""
        psse_uuid = str(uuid4())
        to_psse_queue = Queue()
        from_psse_queue = Queue()
        p = Process(target=PSSE, name=psse_uuid, args=(self.shutdown_event, to_psse_queue, from_psse_queue))

        self.psse_instances[psse_uuid] = {
            "to_psse_queue": to_psse_queue,
            "from_psse_queue": from_psse_queue,
            "process": p,
        }

        p.start()
        await self._get_websocket(request=request, psse_uuid=psse_uuid)

    async def post_psse(self, request:ApiPssePostRequest):
        """Create UUID and intialize and push to queue"""

        psse_uuid = str(uuid4())
        self.uuid_to_project_mapping[psse_uuid] = request.project_name
        to_psse_queue = Queue()
        from_psse_queue = Queue()

        # Create a process for launching PSSE instance
        p = Process(target=PSSE, name=psse_uuid, args=(self.shutdown_event, to_psse_queue, from_psse_queue, request))

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
                message= 'Starting PSSE',
                uuid=psse_uuid,
            )
        except Exception as e:
            self._base_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e), psse_uuid)
  
    async def put_psse(self, request:ApiPssePutRequest):
    
        logger.info(f"Running command :{request.model_dump_json()}")
        self._error_invalid_uuid(request.uuid)
        if not hasattr(request, "command")  or not hasattr(request, "parameters"):            
            self._base_error(HTTPStatus.NOT_FOUND, 'Please provide a command and parameters', request.uuid)

        #psse_t = self.loop.run_in_executor(self.pool, self._post_put_background_task, request.uuid)
        #psse_t.add_done_callback(self._post_put_callback)

        logger.info(f"Submitted data to psse :{request.model_dump_json()}")
        self.psse_instances[str(request.uuid)]["to_psse_queue"].put(request.model_dump_json())
        results = self.psse_instances[str(request.uuid)]["from_psse_queue"].get()

        return ApiPsseReply(
            status='',
            message=f"{results}",
            uuid=request.uuid
        )
        
    async def delete_psse(self, uuid:UUID4):
        """Delete an instance of simulation"""
        self._error_invalid_uuid(uuid)
        try:
            psse_t = self.loop.run_in_executor(self.pool, self._delete_background_task, uuid)
            psse_t.add_done_callback(self._delete_callback)
            self.psse_instances[str(uuid)]["to_psse_queue"].put("END")
            self.psse_instances.pop(str(uuid))
            self.uuid_to_project_mapping.pop(str(uuid))
            return ApiPsseReply(
                status="",
                message="Attempting to close PyPSSE instance",
                uuid = uuid
            ) 
        except Exception:
            msg = f"Error closing in PSSE instance {uuid}"
            logger.error(msg)
            self._base_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error closing in PyPSSE instance", uuid)
    
    async def get_instance_uuids(self):
        """Get all running simulation uuids"""
        uuids = [str(k) for k in self.psse_instances.keys()]
        return ApiPsseReplyInstances(
            status= HTTPStatus.OK,
            message=f"{len(uuids)} uuids found",
            simulators = uuids 
        ) 

    async def get_instance_status(self, uuid:UUID4):
        """Get status of the current provided simuation instance"""
        self._error_invalid_uuid(uuid)
        return ApiPsseReplyInstances(
            status= HTTPStatus.OK,
            message="UUID exists",
            uuid=str(uuid),
        ) 
           
    async def get_download_results(self, uuid:UUID4):
        """Download results from a simulation instance"""
        self._error_invalid_uuid(uuid)
        
        project_name = self.uuid_to_project_mapping[str(uuid)]
        results_file = BASE_PROJECT_PATH / project_name / EXPORTS_FOLDER / DEFAULT_RESULTS_FILENAME
        if not results_file.exists():
            self._base_error(HTTPStatus.NOT_FOUND, "File not found", uuid)
        
        return FileResponse(path=results_file, filename=DEFAULT_RESULTS_FILENAME, media_type='hdf5')
    
    async def get_download_logs(self, uuid:UUID4):
        """Download logs from a simulation instance"""
        if str(uuid) not in self.psse_instances.keys():
            param = "UUID={psse_uuid} not found in the PSSE instances"
            logger.error(f"{param}")
            self._base_error(HTTPStatus.NOT_FOUND, param, uuid)
                    
        project_name = self.uuid_to_project_mapping[str(uuid)]
        results_file = BASE_PROJECT_PATH / project_name / LOGS_FOLDER / DEFAULT_LOG_FILE
        if not results_file.exists():
            self._base_error(HTTPStatus.NOT_FOUND, f"File not found - {results_file}", uuid)
        
        return FileResponse(path=results_file, filename=DEFAULT_LOG_FILE, media_type='hdf5')
        
    def _post_put_background_task(self, psse_uuid):
        q = self.psse_instances[psse_uuid]["from_psse_queue"]
        ans = q.get()
        print("HERE", ans)
        return ans

    def _post_put_callback(self, return_value):
        print(return_value)
        logger.info(f"{return_value.result()}")

    def _get_uuid(self, data):
        if not hasattr(data, "uuid"):
            return None

        psse_uuid = data.uuid
        if psse_uuid not in self.psse_instances.keys():
            return None

        return psse_uuid

    def _delete_background_task(self, psse_uuid:UUID4):
        while self.psse_instances[psse_uuid]["process"].is_alive():
            continue

        del self.psse_instances[psse_uuid]

        return {"Status": "Success", "Message": "PSSE instance closed", "UUID": psse_uuid}

    def _delete_callback(self, return_value):
        logger.info(f"{return_value.result()}")

    def _error_invalid_uuid(self, uuid:UUID4):
        if not uuid or str(uuid) not in self.psse_instances:
            self._base_error(HTTPStatus.NOT_FOUND, "UUID does not exist", uuid)

    def _base_error(self, status_code:HTTPStatus, message:str, uuid:UUID4):
         raise HTTPException(
            status_code=status_code, 
            detail=ApiPsseException(
                message=message,
                uuid=uuid,
                ).model_dump_json()
            )