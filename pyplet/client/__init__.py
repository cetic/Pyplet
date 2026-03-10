"""Client runtime utilities.

This module contains the browser-side bootstrap that loads a packaged micro
app, installs optional Pyodide dependencies, and wires a WebSocket bridge for
real-time communication with the server.

Docstring style: Google.
"""

import asyncio

from js import WebSocket
from pyodide.ffi import create_proxy

import pyplet
from pyplet.utils import get_import


async def bootstrap(project_name, app_name, deps=()):
    """Bootstrap a micro app inside the browser.

    This function is invoked from the HTML shell after unpacking the app zip.
    It optionally installs Pyodide dependencies via ``micropip``, imports the
    client module, runs ``client_init`` if present, and connects the
    ``websocket_client_loop`` if defined.

    Args:
        project_name: Project folder under ``apps/``.
        app_name: Application base name (prefix for ``*_client.py``).
        deps: Optional iterable of extra Pyodide packages to install.
    """
    if deps:
        import pyodide_js

        await pyodide_js.loadPackage("micropip")
        import micropip

        await micropip.install(deps)

    module = get_import(f"apps.{project_name}.{app_name}_client")

    if hasattr(module, "client_init"):
        await module.client_init()

    if hasattr(module, "websocket_client_loop"):
        ws = WebSocket.new(f"/apps/{project_name}/{app_name}_ws")
        ws = ClientWebSocket(ws)
        gen = module.websocket_client_loop(ws)
        ws.ws.onopen = create_proxy(lambda x: asyncio.create_task(gen))


class ClientWebSocket:
    """Thin async wrapper around the browser WebSocket.

    Presents a ``receive`` coroutine that yields text or bytes, and injects the
    ``closing_message`` sentinel when the connection is closed.
    """

    closing_message = pyplet.WebSocket.closing_message

    def __init__(self, javascript_websocket):
        self.ws = javascript_websocket
        self.queue = asyncio.Queue()

        self.ws.onmessage = create_proxy(
            lambda x: asyncio.create_task(self._enqueue_decoded_message(x))
        )
        self.ws.onclose = create_proxy(
            lambda x: asyncio.create_task(self._enqueue_close())
        )

    async def receive(self):
        """Await the next message from the server."""
        return await self.queue.get()

    async def send(self, message):
        """Send a message to the server."""
        return self.ws.send(message)

    async def _enqueue_close(self):
        await self.queue.put(self.closing_message)

    async def _enqueue_decoded_message(self, message):
        data = message.data
        if not isinstance(data, str):
            data = await data.arrayBuffer()
            data = data.to_py().tobytes()
        await self.queue.put(data)
