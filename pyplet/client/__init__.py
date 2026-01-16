import asyncio
from typing import Dict, Tuple

from js import WebSocket
from pyodide.ffi import create_proxy
from importlib import import_module

import pyplet

_apps = None
client_applications: Dict[Tuple[str, str], "ClientApplication"] = {}


async def bootstrap(prefix, project_name, app_name, deps=()):
    global _apps
    _apps = prefix

    if deps:
        import pyodide_js

        await pyodide_js.loadPackage("micropip")
        import micropip

        await micropip.install(deps)

    import_module(f"{_apps}.{project_name}.{app_name}_client")
    client_application = client_applications[project_name, app_name]

    if client_application.__class__.client_init is not ClientApplication.client_init:
        await client_application.client_init()

    if (
        client_application.__class__.websocket_client_loop
        is not ClientApplication.websocket_client_loop
    ):
        ws = WebSocket.new(f"/apps/{project_name}/{app_name}_ws")
        ws = ClientWebSocket(ws)
        gen = client_application.websocket_client_loop(ws)
        ws.ws.onopen = create_proxy(lambda x: asyncio.create_task(gen))


class ClientWebSocket:
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
        return await self.queue.get()

    async def send(self, message):
        return self.ws.send(message)

    async def _enqueue_close(self):
        await self.queue.put(self.closing_message)

    async def _enqueue_decoded_message(self, message):
        data = message.data
        if not isinstance(data, str):
            data = await data.arrayBuffer()
            data = data.to_py().tobytes()
        await self.queue.put(data)


class ClientApplication:
    async def client_init(self): ...
    async def websocket_client_loop(self, ws: ClientWebSocket): ...

    def __init_subclass__(cls):
        qualname = cls.__module__.split(".")
        if (
            qualname[0] == _apps
            and len(qualname) == 3
            and qualname[-1].endswith("_client")
        ):
            _, project_name, app_name = qualname
            app_name = app_name.removesuffix("_client")

            client_applications[project_name, app_name] = cls()
