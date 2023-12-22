# Builtin libraries
import logging

from fastapi import FastAPI
from fastapi import UploadFile
from fastapi.exceptions import HTTPException
import uvicorn
# Internal libraries
from pypsse.api.web.handler import Handler
from pypsse.api.common import BASE_PROJECT_PATH

from pypsse.models import ApiPsseReply
from http import HTTPStatus

import zipfile

logger = logging.getLogger(__name__)

class PSSEServer:
    def __init__(self):
        logger.info("Start PyPSSE server")
        self.handler = Handler()
        logger.info("Building web application")
        self.app = FastAPI()
        self.app.include_router(self.handler.router, prefix='/simulators')
        self.app.add_api_route("/upload_project", self.post_upload_zipped_project, methods=["POST"])
        self.app.add_api_route("/list_projects", self.get_list_projects, methods=["GET"])
        logger.info("Building API endpoints")

    async def cleanup_background_tasks(self):
        logger.info("cleanup_background_tasks")
        self.handler.shutdown_event.set()

    async def get_list_projects(self):
        folders = []
        for x in BASE_PROJECT_PATH.iterdir():
            if x.is_dir():
                print(x)
                folders.append(str(x.name))
        return {"folders" : folders}

    async def post_upload_zipped_project(self, file:UploadFile):
        """Upload a new zipped project to the server"""
        
        try:      
            data = file.file.read()
            if not file.filename.endswith(".zip"):
                raise HTTPException(
                    status_code=HTTPStatus.NOT_ACCEPTABLE, 
                    detail="Invalid file type. Only zip files are accepted."
                    )
            zip_filepath = BASE_PROJECT_PATH / file.filename
            project_path = BASE_PROJECT_PATH / file.filename.replace(".zip", "")
            project_path.mkdir(parents=True, exist_ok=True)
            
            with open(zip_filepath, "wb") as f:
                f.write(data)    
                
            with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                zip_ref.extractall(project_path)
            
            zip_filepath.unlink()
            
            #TODO: update project name and psse path in settings
            
        except Exception as e:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR , detail=str(e))  
        return ApiPsseReply(
            status=HTTPStatus.OK,
            message=f"project upload to {project_path}"
        )

def run_server(host, port):
    print(host, port)
    FORMAT = "%(asctime)s -  %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    # endpoints_file='app/endpoints.yaml'
    instance = PSSEServer()
    uvicorn.run(instance.app, host=host, port=port)


