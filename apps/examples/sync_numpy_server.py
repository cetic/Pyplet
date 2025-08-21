import numpy as np
import base64
import io
import asyncio
import tornado.websocket

client_libraries = ["matplotlib", "numpy"]


sockets = []


async def websocket_server_loop(ws):
    sockets.append(ws)


async def send_to_all():
    while True:
        if sockets:
            bytes = io.BytesIO()
            array = np.random.randn(10, 10)
            np.save(bytes, array)
            value = bytes.getvalue()
            for ws in list(sockets):
                try:
                    await ws.send(value)
                except tornado.websocket.WebSocketClosedError:
                    sockets.remove(ws)
        await asyncio.sleep(1)


asyncio.create_task(send_to_all())
