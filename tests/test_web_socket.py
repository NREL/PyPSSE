from websockets.sync.client import connect

from pypsse.enumerations import ApiCommands
from pypsse.models import ApiAssetQuery, ApiWebSocketRequest

conn = connect("ws://127.0.0.1:9090/simulator/ws")

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
    results = conn.recv()
    print(results)  # noqa

    request = ApiWebSocketRequest(
        command=ApiCommands.QUERY_BY_PPTY.value,
        parameters=ApiAssetQuery(asset_type="Buses", asset_property="PU", asset_id="153").model_dump(),
    )

    conn.send(request.model_dump_json())
    results = conn.recv()
    print(results)  # noqa


request_end = "END"

conn.send(request_end)
results = conn.recv()
print(results)  # noqa

conn.close()
