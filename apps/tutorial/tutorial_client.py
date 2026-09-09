from js import document

import pyplet
from pyplet.shared.dom import div, download, h1, h2, hr, p, upload, upload_area

container = document.getElementById("container")


class MyClientApp(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        container.innerHTML = str(
            # Main Wrapper: Centers the content and
            # limits width for readability
            div(
                style=(
                    "max-width: 800px; margin: 40px auto; "
                    "font-family: sans-serif; padding: 20px;"
                )
            )[
                # Page Header
                h1(style="margin-bottom: 10px;")[
                    "Pyplet File Operations Tutorial"
                ],
                p(style="color: #666; font-size: 1.1em;")[
                    (
                        "Explore how to handle file uploads and "
                        "downloads using custom components."
                    )
                ],
                hr(
                    style=(
                        "margin: 30px 0; border: none;"
                        "border-top: 1px solid #eee;"
                    )
                ),
                # --- SECTION 1: Downloads ---
                div(style="margin-bottom: 40px;")[
                    h2(style="margin-bottom: 10px;")["1. Downloading Files"],
                    p(style="margin-bottom: 20px; color: #444;")[
                        (
                            "Test downloading files directly from the server"
                            " versus the client's Virtual File System (VFS)."
                        )
                    ],
                    # Flex container to place buttons side-by-side cleanly
                    div(style="display: flex; gap: 15px;")[
                        download(
                            "./static/static_file.txt",
                            "⬇ Download from Server",
                        ),
                        download(
                            "./public/vfs_file.txt",
                            "⬇ Download from Client (VFS)",
                            from_vfs=True,
                        ),
                    ],
                ],
                hr(
                    style=(
                        "margin: 30px 0; border: none;"
                        "border-top: 1px solid #eee;"
                    )
                ),
                # --- SECTION 2: Uploads ---
                div(style="margin-bottom: 40px;")[
                    h2(style="margin-bottom: 10px;")["2. Uploading Files"],
                    p(style="margin-bottom: 20px; color: #444;")[
                        "Upload files using a standard button, "
                        "or use the drag-and-drop area for multiple files."
                    ],
                    # Standard Button Upload
                    div(style="margin-bottom: 30px;")[
                        upload(
                            "path/to/file.txt",
                            "⇧ Standard Upload Button",
                            server_destination="/uploads",
                            client_destination="./public/uploads",
                        ),
                    ],
                    # Drag and Drop Area
                    div[
                        upload_area(
                            client_destination="path/to/dir",
                            text="Drag and drop your tutorial files here",
                        ),
                    ],
                ],
            ]
        )

        await ws.send("Hello world!")
