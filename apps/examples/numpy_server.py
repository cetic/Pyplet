import numpy as np
import base64
import io
import asyncio
import tornado.websocket

client_libraries = ["matplotlib", "numpy"]
sockets = []


async def websocket_server_loop(ws):
    sockets.append(ws)
    while True:
        bytes = io.BytesIO()
        array = np.random.randn(10, 10)
        np.save(bytes, array)
        try:
            await ws.send(bytes.getvalue())
        except tornado.websocket.WebSocketClosedError:
            break
        print(array)
        await asyncio.sleep(1)
    sockets.remove(ws)
