async def bootstrap(project_name, app_name, deps=()):
    import glob

    # print(glob.glob("**", recursive=True))
    from js import WebSocket
    from pyodide.ffi import create_proxy
    from pyplet.common.utils import get_import
    import asyncio

    if deps:
        import pyodide_js

        await pyodide_js.loadPackage("micropip")
        import micropip

        await micropip.install(deps)

    module = get_import(f"apps.{project_name}.{app_name}_client")

    if hasattr(module, "client_init"):
        await module.client_init()

    if hasattr(module, "websocket_client_loop"):
        queue = asyncio.Queue()

        async def aclose():
            await queue.put(StopIteration)

        async def asend_decoded(message):
            data = message.data
            if not isinstance(data, str):
                data = await data.arrayBuffer()
                data = data.to_py().tobytes()
            await queue.put(data)

        async def receive():
            return await queue.get()

        ws = WebSocket.new(f"/apps/{project_name}/{app_name}_ws")
        gen = module.websocket_client_loop(ws)
        ws.receive = receive
        ws.onopen = create_proxy(lambda x: asyncio.create_task(gen))
        ws.onmessage = create_proxy(lambda x: asyncio.create_task(asend_decoded(x)))
        ws.onclose = create_proxy(lambda x: asyncio.create_task(aclose()))
