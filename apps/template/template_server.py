# The template file must be written i used chat_server example temporarly
import asyncio
import pyplet
import json

available = ["jack", "denis", "max"]
sockets = {}


async def websocket_server_loop(ws: pyplet.WebSocket):
    if not available:
        await ws.send(
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
    await ws.send(
        json.dumps(
            {
                "type": "init",
                "name": name,
            }
        )
    )
    while True:
        msg = await ws.receive()
        if msg is ws.closing_message:
            break
        msg = json.dumps(
            {
                "type": "message",
                "name": name,
                "message": msg,
            }
        )
        await asyncio.gather(*(s.send(msg) for s in sockets.values()))
    del sockets[name]
    available.insert(0, name)
