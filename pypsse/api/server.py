# Builtin libraries
import logging
import zipfile
from contextlib import asynccontextmanager
from http import HTTPStatus

import uvicorn
from fastapi import FastAPI, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse

from pypsse.api.common import BASE_PROJECT_PATH

# Internal libraries
from pypsse.api.web.handler import Handler
from pypsse.models import ApiPsseReply

logger = logging.getLogger(__name__)


class Server:
    def __init__(self):
        """Creates FAST API app to be served"""
        logger.info("Start server")
        self.handler = Handler()
        logger.info("Building web application")
        self.app = FastAPI(lifespan=self.lifespan)
        self.app.include_router(self.handler.router, prefix="/simulator")
        self.app.add_api_route("/", self.get_main_page, methods=["GET"])
        self.app.add_api_route("/upload", self.post_upload_zipped_project, methods=["POST"])
        self.app.add_api_route("/projects", self.get_list_projects, methods=["GET"])

        logger.info("Building API endpoints")

    async def get_main_page(self) -> HTMLResponse:
        """returns an html main page

        Returns:
            HTMLResponse: html page for base server url
        """

        html = """
        <h1>PyPSSE Server</h1>

        <h3>
        PyPSSE is a Python wrapper around psspy—a Python application programming
        interface (API) for the Power System Simulator for Engineering (PSS/E)—to perform
        time series power flow and dynamic simulation for power systems.
        </h3>

        <h3>
        The PSS/E Python API psspy follows functional programming methodology. The API
        exposes thousands of methods and can be difficult for new users to work with.
        PyPSSE wraps around hundreds of function calls in a few methods. This functionality
        allows users to set up cosimulations with minimal effort.
        </h3>

        <h3>For more information see check out the <a href="https://nrel.github.io/PyPSSE/">documentation</a></h3>

        <h3>For swagger documentation see: <a href="http://127.0.0.1:9090/docs/">SwaggerDocs</a></h3>

        <h3>For redoc documentation see: <a href="http://127.0.0.1:9090/redoc/">ReDoc</a></h3>

        """
        return HTMLResponse(html)

    @asynccontextmanager
    async def lifespan(self, *_, **__):
        """lifespan manager for the app. handeles logic for application startup and shutdown."""

        yield
        logger.info("cleanup_background_tasks")
        self.handler.shutdown_event.set()

    async def get_list_projects(self) -> list:
        """methods finds and returns pypsse projects

        Returns:
            list: returns a list of projects available on the server
        """

        folders = []
        for x in BASE_PROJECT_PATH.iterdir():
            if x.is_dir():
                folders.append(str(x.name))
        return {"folders": folders}

    async def post_upload_zipped_project(self, file: UploadFile):
        """upload a new zipped project to the server

        Args:
            file (UploadFile): _description_

        Raises:
            HTTPException: raised if invalid file exception
            HTTPException: raised if unexpected error happens server side

        Returns:
            ApiPsseReply: request returned
        """

        try:
            data = file.file.read()
            if not file.filename.endswith(".zip"):
                raise HTTPException(
                    status_code=HTTPStatus.NOT_ACCEPTABLE, detail="Invalid file type. Only zip files are accepted."
                )
            zip_filepath = BASE_PROJECT_PATH / file.filename
            project_path = BASE_PROJECT_PATH / file.filename.replace(".zip", "")
            project_path.mkdir(parents=True, exist_ok=True)

            with open(zip_filepath, "wb") as f:
                f.write(data)

            with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
                zip_ref.extractall(project_path)

            zip_filepath.unlink()

            # TODO: update project name and psse path in settings

        except Exception as e:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))
        return ApiPsseReply(status=HTTPStatus.OK, message=f"project upload to {project_path}")


def run_server(host: str, port: int):
    """Start the pypsse server

    Args:
        host (str): server ip adadress (set to switch between internal or external ip)
        port (int): server port
    """
    time_format = "%(asctime)s -  %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=time_format)
    # endpoints_file='app/endpoints.yaml'
    instance = Server()
    uvicorn.run(instance.app, host=host, port=port)
