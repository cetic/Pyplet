import logging

import pyplet


class _(pyplet.server.ServerApplication):
    title = "Hello World"
    interpreter = "mpy"

    async def websocket_server_loop(self, ws: pyplet.WebSocket):
        await ws.send("Hello world!")
        logging.warning(await ws.receive())
