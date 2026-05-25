from js import document

import pyplet
from pyplet.shared.dom import div, download, upload, upload_area

container = document.getElementById("container")


class MyClientApp(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        container.innerHTML = str(
            div[
                download(
                    "./static/static_file.txt",
                    "Download from server",
                ),
                download(
                    "./public/vfs_file.txt",
                    "Download from client",
                    from_vfs=True,
                ),
                upload("path/to/file.txt", "Upload File"),
                upload_area("path/to/dir", "Upload Directory"),
            ]
        )
        # container.innerText = await ws.receive()

        await ws.send("Hello world!")
