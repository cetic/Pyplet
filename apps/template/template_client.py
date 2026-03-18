from js import document

import pyplet

container = document.getElementById("container")


class _(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        container.innerText = await ws.receive()

        await ws.send("Hello world!")
