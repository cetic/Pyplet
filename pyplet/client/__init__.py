import collections
import sys
from importlib import import_module
from typing import Dict, Tuple

from js import WebSocket

try:
    # 1. Try Pyodide / CPython standard library
    import asyncio

    try:
        from pyodide.ffi import create_proxy
    except ImportError:
        create_proxy = lambda x: x  # noqa: E731

except ImportError:
    # 2. MicroPython Fallback
    import js

    # Inject a tiny JS helper to create a safe Deferred promise across FFI
    js.eval("""
    if (!globalThis.create_deferred) {
        globalThis.create_deferred = function() {
            let res;
            let p = new Promise(r => res = r);
            return {promise: p, resolve: res};
        };
    }
    """)

    # Build a native JS-Promise event loop to drive Python coroutines!
    class AsyncioPolyfill:
        @staticmethod
        def create_task(coro):
            def step(val=None):
                try:
                    # Advance the Python coroutine
                    prom = coro.send(val)

                    # If the coroutine yielded a JS Promise, hook into it!
                    if hasattr(prom, "then"):
                        prom.then(step)
                    else:
                        # Otherwise, continue on the next JS engine tick
                        js.Promise.resolve(prom).then(step)
                except StopIteration:
                    pass
                except Exception as e:
                    import sys

                    sys.print_exception(e)

            # Kickstart the task
            step()
            return coro

    asyncio = AsyncioPolyfill()

    # Polyfill Queue using JS Promises bridging to the browser event loop
    class AsyncQueue:
        def __init__(self, maxsize=0):
            self._queue = collections.deque()
            self._resolve = None
            self._promise = None
            self._reset_promise()

        def _reset_promise(self):
            # Let JavaScript create the promise and
            # the resolver function safely
            deferred = js.create_deferred()
            self._promise = deferred.promise
            self._resolve = deferred.resolve

        async def put(self, item):
            self._queue.append(item)
            # Signal the JS event loop to wake up the get() await
            if self._resolve:
                self._resolve(None)

        async def get(self):
            # MicroPython uses __iter__ for awaitables!
            class AwaitPromise:
                def __init__(self, promise):
                    self.promise = promise

                def __iter__(self):
                    yield self.promise

            while not self._queue:
                # Safely yield the JS Promise out to our Polyfill task driver
                await AwaitPromise(self._promise)
                self._reset_promise()

            return self._queue.popleft()

    asyncio.Queue = AsyncQueue

    # MicroPython passes JS boundaries natively, no proxy needed
    create_proxy = lambda x: x  # noqa: E731


import pyplet

_apps = None
client_applications: Dict[Tuple[str, str], "ClientApplication"] = {}


async def bootstrap_client(prefix, project_name, app_name, deps=()):
    global _apps
    _apps = prefix

    if deps:
        if sys.implementation.name == "micropython":
            import mip

            for dep in deps:
                mip.install(dep)
        else:
            import micropip

            await micropip.install(list(deps))

    # 1. Capture the returned module object
    mod = import_module(f"{_apps}.{project_name}.{app_name}_client")

    # 2. Try standard Pyodide dictionary lookup
    # (populated by __init_subclass__)
    if (project_name, app_name) in client_applications:
        client_application = client_applications[project_name, app_name]

    # 3. MicroPython Fallback: Inspect the module directly
    else:
        found_class = None
        for item_name in dir(mod):
            item = getattr(mod, item_name)
            if (
                isinstance(item, type)
                and issubclass(item, ClientApplication)
                and item is not ClientApplication
            ):
                found_class = item
                break

        if not found_class:
            raise RuntimeError(
                "Could not find a ClientApplication "
                f"subclass in {project_name}/{app_name}"
            )

        # Instantiate it and manually register it
        client_application = found_class()
        client_applications[project_name, app_name] = client_application

    if (
        client_application.__class__.client_init
        is not ClientApplication.client_init
    ):
        await client_application.client_init()

    if (
        client_application.__class__.websocket_client_loop
        is not ClientApplication.websocket_client_loop
    ):
        ws = WebSocket.new(f"/apps/{project_name}/{app_name}.ws")
        ws_wrapper = ClientWebSocket(ws)
        gen = client_application.websocket_client_loop(ws_wrapper)

        # Use our driver to trigger the loop when JS says the socket is open
        ws.onopen = create_proxy(lambda event: asyncio.create_task(gen))


class ClientWebSocket:
    closing_message = pyplet.WebSocket.closing_message

    def __init__(self, javascript_websocket):
        self.ws = javascript_websocket
        self.queue = asyncio.Queue()

        self.ws.onmessage = create_proxy(
            lambda event: asyncio.create_task(
                self._enqueue_decoded_message(event)
            )
        )
        self.ws.onclose = create_proxy(
            lambda event: asyncio.create_task(self._enqueue_close())
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
            # Engine-agnostic ArrayBuffer handling
            if hasattr(data, "arrayBuffer"):
                data = await data.arrayBuffer()

            # Cross-engine byte conversions
            if hasattr(data, "to_py"):
                data = data.to_py().tobytes()
            elif hasattr(data, "tobytes"):
                data = data.tobytes()
            else:
                data = bytes(data)  # MicroPython memoryview fallback

        await self.queue.put(data)


class ClientApplication:
    async def client_init(self): ...
    async def websocket_client_loop(self, ws: "ClientWebSocket"): ...

    def __init_subclass__(cls):
        qualname = cls.__module__.split(".")

        # Pyodide / CPython standard behavior
        if (
            qualname[0] == _apps
            and len(qualname) >= 3
            and qualname[-1].endswith("_client")
        ):
            project_name = qualname[-2]
            app_name = qualname[-1].removesuffix("_client")
            client_applications[project_name, app_name] = cls()
