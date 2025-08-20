import json
import asyncio

available = ["jack", "denis", "max"]
sockets = {}


async def websocket_server_loop(ws):
    if not available:
        ws.send(
            json.dumps(
                {
                    "type": "error",
                    "message": "No user left",
                }
            )
        )
        return

    name = available.pop()
    sockets[name] = ws
    ws.send(
        json.dumps(
            {
                "type": "init",
                "name": name,
            }
        )
    )
    while True:
        msg = await ws.receive()
        if msg is StopIteration:
            break
        msg = json.dumps(
            {
                "type": "message",
                "name": name,
                "message": msg,
            }
        )
        await asyncio.gather(*(s.send(msg) for s in sockets.values()))
    print(f"User {name} left.")
    del sockets[name]
    available.insert(0, name)
