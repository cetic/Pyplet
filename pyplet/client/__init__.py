from js import WebSocket
from pyodide.ffi import create_proxy
from pyplet.utils import get_import
import pyplet
import asyncio


async def bootstrap(project_name, app_name, deps=()):
    import glob

    # print(glob.glob("**", recursive=True))

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
