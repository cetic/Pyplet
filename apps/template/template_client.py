from js import document

import pyplet
from pyplet.shared.dom import div, download, upload, upload_area

container = document.getElementById("container")


class MyClientApp(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        container.innerHTML = str(
            div[
                download("path/to/file.txt", "Download File"),
                download("path/to/file_2.txt", "Download File 2"),
                upload("path/to/file.txt", "Upload File"),
                upload_area("path/to/dir", "Upload Directory"),
            ]
        )
        # container.innerText = await ws.receive()

        await ws.send("Hello world!")
