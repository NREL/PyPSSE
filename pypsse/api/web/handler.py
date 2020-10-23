# Built-in Libraries
import os
import json
import logging
import asyncio
from uuid import uuid4
from aiohttp_swagger import *
from multiprocessing import Queue, Process, Event, cpu_count
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# External libraries
from aiohttp import web, WSMsgType

# Internal Libraries
from pypsse.api.app.psse import PSSE

logger = logging.getLogger(__name__)

class Handler:

    """ Handlers for web server. """

    def __init__(self):
        
        """ Constructor for PSSE handler. """
        
        logger.info("Initializing Handler ....")

        # Initializing dictionary for stroing psse_instances
        self.psse_instances = dict()

        # Event flag to control shutdown of background tasks
        self.shutdown_event = Event()

        # Pool and Loop are used to catch returning Multiprocessing Queue messages
        #  to prevent blocking of the API.  

        self.pool = ThreadPoolExecutor(max_workers=cpu_count()-1)
        self.loop = asyncio.get_event_loop()
        

    # Websocket calls for PSSE
    async def get_psse(self, request):

        """Websocket handler for psse instance"""
        psse_uuid = str(uuid4())
        to_psse_queue = Queue()
        from_psse_queue = Queue()
        p = Process(target=PSSE, name=psse_uuid, 
        args=(self.shutdown_event, to_psse_queue,from_psse_queue))

        self.psse_instances[psse_uuid] = {
            "to_psse_queue": to_psse_queue,
            "from_psse_queue": from_psse_queue,
            "process": p
        }

        p.start()
        await self._get_websocket(request=request, psse_uuid=psse_uuid)
    
    async def _get_websocket(self, request, psse_uuid):

        to_psse_queue = self.psse_instances[psse_uuid]["to_psse_queue"]
        from_psse_queue = self.psse_instances[psse_uuid]["from_psse_queue"]

        logger.info(f"starting websocket connection for {psse_uuid}")
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        logger.info(f"websocket connection ready, type={type(ws)}")

        # Receive the initial response back from psse
        result = from_psse_queue.get()
        logger.info(f"handler psse result = {result}")
        await ws.send_str(json.dumps(result))

        async for msg in ws:
            logger.info(f"websocket message: {msg}")

            if msg.type == WSMsgType.TEXT:

                logger.info(f"websocket message data: {msg.data}")

                # Pushing data from client to psse
                to_psse_queue.put(msg.data)

                # receive result back from psse
                result = from_psse_queue.get()
                logger.info(f"psse handler output = {result}")

                await ws.send_str(json.dumps(result))
                

                if msg.data == "END":
                    await ws.close()

        logger.info(f"websocket connection closed")

        return ws
    # REST API Calls
    async def post_psse(self, request):

        
        """
        ---
        summary: Creates a PyPSSE instance 
        tags:
            - simulation
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            parameters:
                                type: object
                    examples:
                        Example 1:
                            value:
                                parameters:
                                    filename: C:/Users/alatif/Desktop/pypsse-code/examples/static_example/Settings/pyPSSE_settings.toml
        responses:
            "200":
                description: creates an instance successfully.
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            post_message:
                                value:
                                    Status: Success,
                                    Message: 'Starting PSSE'
                                    UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6

            "500":
                description: Failed creating a psse instance
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            post_message:
                                value:
                                    Status: Failed,
                                    Message: Failed creating an instance
                                    UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
        """

        # Create UUID and intialize Queue

        data = await request.json()
        print("Request body: ", data)
        params = data['parameters']
        psse_uuid = str(uuid4())
        to_psse_queue = Queue()
        from_psse_queue = Queue()

        # Create a process for launching PSSE instance
        p = Process(target=PSSE, name=psse_uuid, args=(self.shutdown_event, to_psse_queue, from_psse_queue, params))

        # Store queue and process
        self.psse_instances[psse_uuid] = {
            "to_psse_queue": to_psse_queue,
            "from_psse_queue": from_psse_queue,
            "process": p
            }

        # Catching data coming from PSSE
        psse_t = self.loop.run_in_executor(self.pool, self._post_put_background_task, psse_uuid)
        psse_t.add_done_callback(self._post_put_callback)

        # Start process for psse
        try:
            p.start()

            # Return a message to webclient
            result = {'Status':'Success',
                    'Message': 'Starting PSSE',
                    'UUID': psse_uuid}
        
            return web.Response(text=json.dumps(result),status=200)
        
        except Exception as e:
            return web.Response(text=json.dumps({
                'Status': 'Failed',
                'Message': str(e)
            }), status=500)

    async def put_psse(self, request):

        """
        ---
        summary: Run a command on an instance of PyPSSE.
        tags:
            - simulation
       
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            UUID:
                                type: string
                                format: UUID
                                example: 96c21e00-cd3c-4943-a914-14451f5f7ab6
                            command: 
                                type: string
                                example: open_case
                            parameters:
                                type: object
                    examples:
                        Example 1:
                            value:
                                UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
                                command: init
                                parameters: {}
                        Example 2:
                            value:
                                UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
                                command: solve_step
                                parameters: {}
                        Example 3:
                            value:
                                UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
                                command: get_results
                                parameters:
                                    params:
                                        Loads:
                                            id_fields: ["MVA"]
                                        Buses:
                                            id_fields: ["PU", "ANGLE"]
        responses:
            "200":
                description: Success on placing command.
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            command_placed_psse:
                                value:
                                    Status: Success
                                    Message: init command submitted, awaiting response 
                                    UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
            "500":
                description: Failed placing a acommand
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            command_placed_psse:
                                value:
                                    code: 500
                                    message: Error placing command
        """
        
        
        data = await request.json()
        logger.info(f"Running command :{data}")

        if "command" not in data or "parameters" not in data:
           
            msg = "Please provide a command and parameters"
            
            logger.error(msg)

            return web.json_response({"Status":"Failed","Message":msg,"UUID":None})

        psse_uuid = self._get_uuid(data=data)
        if psse_uuid:
            psse_t = self.loop.run_in_executor(self.pool, self._post_put_background_task, psse_uuid)
            psse_t.add_done_callback(self._post_put_callback)

            logger.info(f"Submitted data to psse :{data}")
            self.psse_instances[psse_uuid]['to_psse_queue'].put(json.dumps(data))

            result = {"Status":"Success",
                      "Message":f"{data['command']} command submitted, awaiting response ",
                      "UUID":psse_uuid
                      }
            return web.Response(text=json.dumps(result),status=200)
        else:
            param = "UUID={psse_uuid} not found in the PSSE instances"
            logger.error(f"{param}")
            return "error"

    async def delete_psse(self, request):

        """
        ---
        summary: Deletes an active instance of PyPSSE.
        tags:
            -   simulation
        parameters:
            -   in: path
                name: uuid
                required: true
                schema:
                    type: string
                    format: UUID
                    example: 96c21e00-cd3c-4943-a914-14451f5f7ab6
            
        responses:
            "200":
                description: deletes an instance successfullly.
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            delete_instance:
                                value:
                                    Status: Success
                                    Message: Attempting to close psse instance
                                    UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
            "500":
                description: Failed deleting a psse instance
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            delete_instance:
                                value:
                                    code: 500
                                    message: Error closing in PSSE instance 96c21e00-cd3c-4943-a914-14451f5f7ab6
                                    
        """

        psse_uuid = request.match_info['uuid']
    

        if psse_uuid not in self.psse_instances.keys():

            param = "UUID={psse_uuid} not found in the PSSE instances"
            logger.error(f"{param}")
            return -1

        try:
            psse_t = self.loop.run_in_executor(self.pool,self._delete_background_task,psse_uuid)
            psse_t.add_done_callback(self._delete_callback)

            self.psse_instances[psse_uuid]["to_psse_queue"].put("END")

            return web.Response(text= json.dumps({
                "Status": "Success",
                "Message": f"Attempting to close psse instance",
                "UUID": psse_uuid
            }),status=200)
        except Exception as e:
            msg = f"Error closing in PSSE instance {psse_uuid}"
            return -1

    async def get_instance_uuids(self, request):

        """
        ---
        summary: Returns UUIDs of all instances running on the server
        tags:
            -   simulation status
        
        responses:
            "200":
                description: lists all PyPSSE instances.
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            get_uuid_instances:
                                value:
                                    Status: Success
                                    Instances: []
        """
        
        uuids = [str(k) for k in self.psse_instances.keys()]
        return web.json_response({
            "Status": "Success",
            "Instances": uuids
        })

    async def get_instance_status(self, request):

        """
        ---
        summary: This end-point gives the status of PyPSSE instance.
        tags:
            -   simulation status

        parameters:
            -   name: uuid
                in: path
                required: true
                schema:
                    type: string
                    format: UUID
                    example: 96c21e00-cd3c-4943-a914-14451f5f7ab6


        responses:
            "200":
                description: Fetched the psse instance status successfully .
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            get_instance_status:
                                value:
                                    Status: Success
                                    Message: None
                                    UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
            "500":
                description: Failed fetching the psse instance status. 
                content:
                    application/json:
                        schema:
                            type: object
                        examples:
                            get_instance_status:
                                value:
                                    Status: Failed
                                    Message: Does not exists
                                    UUID: 96c21e00-cd3c-4943-a914-14451f5f7ab6
        """
        psse_uuid = request.match_info['uuid']

        if psse_uuid:
            status = "Success"
            msg = None
        else:
            status = "Failed"
            msg = "Does not exist"
        
        status_code = 200 if status=='Success' else 500
        return web.Response(text=json.dumps({
            "Status":status,
            "Message":msg,
            "UUID": psse_uuid
        }),status=status_code)

    def _post_put_background_task(self, psse_uuid):
        q = self.psse_instances[psse_uuid]["from_psse_queue"]
        return q.get()

    def _post_put_callback(self, return_value):

        logger.info(f"{return_value.result()}")

    def _get_uuid(self, data):

        if "UUID" not in data:
            return None
        
        psse_uuid = data['UUID']
        if psse_uuid not in self.psse_instances.keys():
            return None
        
        return psse_uuid
    
    def _delete_background_task(self, psse_uuid):

        while self.psse_instances[psse_uuid]["process"].is_alive():
            continue

        del self.psse_instances[psse_uuid]

        return {
            "Status":"Success",
            "Message":"PSSE instance closed",
            "UUID": psse_uuid
        }

    def _delete_callback(self, return_value):
        logger.info(f"{return_value.result()}")

