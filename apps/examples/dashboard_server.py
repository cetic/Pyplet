import json

from . import chat_server
from . import numpy_server
from . import sync_numpy_server

import tornado.websocket

import asyncio

client_libraries = ["matplotlib"]

historical_data = {
    "chat_server": [],
    "numpy_server": [],
    "sync_numpy_server": [],
    "dashboard_server": [],
}
sockets = []


async def sample():
    while True:
        live = {
            "chat_server": len(chat_server.sockets),
            "numpy_server": len(numpy_server.sockets),
            "sync_numpy_server": len(sync_numpy_server.sockets),
            "dashboard_server": len(sockets),
        }
        for s in list(sockets):
            try:
                await s.send(json.dumps(live))
            except tornado.websocket.WebSocketClosedError:
                sockets.remove(s)
        for l in live:
            historical_data[l].append(live[l])
        await asyncio.sleep(1)


asyncio.create_task(sample())


async def websocket_server_loop(ws):
    ws.send(json.dumps(historical_data))
    sockets.append(ws)
