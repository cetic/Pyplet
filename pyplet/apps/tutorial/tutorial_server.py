import logging

import pyplet


class _(pyplet.server.ServerApplication):
    title = "Hello World"
    interpreter = "py"

    async def websocket_server_loop(self, ws: pyplet.WebSocket):
        await ws.send("Hello from tutorial server!")
        logging.warning(await ws.receive())
