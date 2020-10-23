# Builtin libraries
import logging
import os
import time
from http import HTTPStatus
import threading
import requests
import json

# Internal libraries
from pypsse.api.web.handler import Handler
from aiohttp_swagger3 import *
from aiohttp import web

logger = logging.getLogger(__name__)

def get_jsonschema(host,port):
    path = os.path.join(os.path.dirname(__file__), '../api/PSSE.v2.json')
    base_url = f"http://{host}:{port}"
    url = base_url + "/docs/swagger.json"
    is_valid = False
    while not is_valid:
        time.sleep(3)
        response = requests.get(url)
        is_valid = response.status_code == HTTPStatus.OK
    with open(path, 'w') as outfile:
        json.dump(response.json(), outfile, indent=4, sort_keys=True)
    logger.info(f"Export the schema file to {path}")

class PSSEServer:
    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.handler = Handler()
        self.app = web.Application()
        # setup_swagger(self.app,swagger_url="/api/doc")
        self.swagger = SwaggerDocs(
            self.app,
            title='psse_service RESTful API documentation',
            description="Create PyPSSE instance, run simulation, get status of running instance, delete running instance etc.",
            swagger_ui_settings=SwaggerUiSettings(path='/docs/')
        )
        self.add_routes()
        self.t = threading.Thread(name='model_generator_thread', target=get_jsonschema, args=(self.host,self.port))
        self.t.start()

    def add_routes(self):
        """
        Methods to add all HTTP routes
        """
        # Websocket
        self.app.router.add_get('/simulators/psse', self.handler.get_psse)
        self.swagger.add_routes([
            web.get('/simulators/psse/instances', self.handler.get_instance_uuids),
            web.get('/simulators/psse/status/uuid/{uuid}', self.handler.get_instance_status),
            web.put('/simulators/psse', self.handler.put_psse),
            web.post('/simulators/psse', self.handler.post_psse),
            web.delete('/simulators/psse/uuid/{uuid}', self.handler.delete_psse)
        ])
        # TODO: adding routes to print all commands /simulators/psse/get_available_commands

    async def cleanup_background_tasks(self,app):
        logger.info("cleanup_background_tasks")
        self.t.join()
        self.handler.shutdown_event.set()


if __name__ == "__main__":
    FORMAT = '%(asctime)s -  %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO,format=FORMAT)
    #endpoints_file='app/endpoints.yaml'
    instance = PSSEServer()