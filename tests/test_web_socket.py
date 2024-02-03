from fastapi.testclient import TestClient
from websockets.sync.client import connect
import subprocess
import os, signal
import json

from pypsse.api.server import Server
from pypsse.enumerations import ApiCommands
from pypsse.models import ApiAssetQuery, ApiWebSocketRequest


server = Server()

client = TestClient(server.app)


# def test_web_sockt_interface():
#     with client.websocket_connect("/simulator/ws") as conn:
#         request = ApiWebSocketRequest(command=ApiCommands.STATUS, parameters=None)

#         conn.send(request.model_dump_json())
#         results = conn.receive_json()
#         print(results)  #cl noqa

#         request = ApiWebSocketRequest(command=ApiCommands.OPEN_CASE, parameters={"project_name": "static_example"})
#         conn.send_json(request.model_dump_json())
#         results = conn.receive_json()
#         print(results)  # noqa

#         for _ in range(10):
#             request = ApiWebSocketRequest(command=ApiCommands.SOLVE_STEP.value, parameters=None)
#             conn.send_json(request.model_dump_json())
#             results = conn.receive_json()
#             print(results)  # noqa

#             request = ApiWebSocketRequest(
#                 command=ApiCommands.QUERY_BY_PPTY.value,
#                 parameters=ApiAssetQuery(asset_type="Buses", asset_property="PU", asset_id="153").model_dump(),
#             )

#             conn.send_json(request.model_dump_json())
#             results = conn.receive_json()
#             print(results)  # noqa

#         request_end = "END"

#         conn.send_json(request_end)
#         results = conn.receive_json()
#         print(results)  # noqa




def test_web_sockt_interface_manual():
    
    process = subprocess.Popen("pypsse serve")
    
    conn = connect("ws://127.0.0.1:9090/simulator/ws")
    results = json.loads(conn.recv())
    request = ApiWebSocketRequest(command=ApiCommands.STATUS, parameters=None)

    conn.send(request.model_dump_json())
    results = conn.recv()
    print(results)  # noqa

    request = ApiWebSocketRequest(command=ApiCommands.OPEN_CASE, parameters={"project_name": "static_example"})

    conn.send(request.model_dump_json())
    results = conn.recv()
    print(results)  # noqa

    for _ in range(10):
        request = ApiWebSocketRequest(command=ApiCommands.SOLVE_STEP.value, parameters=None)
        conn.send(request.model_dump_json())
        results = json.loads(conn.recv())

        request = ApiWebSocketRequest(
            command=ApiCommands.QUERY_BY_PPTY.value,
            parameters=ApiAssetQuery(asset_type="Buses", asset_property="PU", asset_id="153").model_dump(),
        )

        conn.send(request.model_dump_json())
        results = json.loads(conn.recv())
        print(results["message"])  # noqa

    request_end = "END"

    conn.send(request_end)
    results = conn.recv()
    print(results)  # noqa

    conn.close()
    process.terminate()
