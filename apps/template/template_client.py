from js import document

import pyplet
from pyplet.shared.dom import download

container = document.getElementById("container")


class MyClientApp(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        container.innerHTML = str(
            download("path/to/file.txt", "Download File")
        )
        # container.innerText = await ws.receive()

        await ws.send("Hello world!")
