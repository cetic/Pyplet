import base64
import collections
import os
import sys
from importlib import import_module
from typing import Dict, Tuple

import js
from js import WebSocket

try:  # noqa: C901
    if sys.implementation.name == "micropython":
        raise ImportError("asyncio Queue are not available on MicroPython")

    # 1. Try Pyodide / CPython standard library
    import asyncio

    try:
        from pyodide.ffi import create_proxy
    except ImportError:
        create_proxy = lambda x: x  # noqa: E731

except ImportError:
    # This should not be used with the current version of
    # MicroPython (>= 2026.3.1)
    print(
        "Warning: asyncio not available, "
        + "falling back to MicroPython JS polyfill"
    )
    # 2. MicroPython Fallback
    # Inject a tiny JS helper to create a safe Deferred promise across FFI
    js.eval("""
if (!globalThis.create_deferred) {
    globalThis.create_deferred = function() {
        let res;
        let p = new Promise(r => res = r);
        return {promise: p, resolve: res};
    };
}""")

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
            # CPython allows infinite queues (maxsize=0).
            # MicroPython strictly requires a maxlen.
            # We default to 100 if unbounded.
            queue_limit = maxsize if maxsize > 0 else 100

            try:
                # Try the MicroPython strict signature first
                self._queue = collections.deque((), queue_limit)
            except TypeError:
                # Fallback for standard CPython/Pyodide just in case
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
                # Safely yield the JS Promise out
                # to our Polyfill task driver
                await AwaitPromise(self._promise)
                self._reset_promise()

            return self._queue.popleft()

    asyncio.Queue = AsyncQueue

    # MicroPython passes JS boundaries natively, no proxy needed
    create_proxy = lambda x: x  # noqa: E731


import pyplet

VFS_UPLOAD_JAIL = "/vfs_uploads"
SERVER_UPLOAD_JAIL = "server_uploads"
MAX_UPLOAD_SIZE = 50 * 2**20  # 50 MiB

_apps = None
client_applications: Dict[Tuple[str, str], "ClientApplication"] = {}


def _setup_vfs_bindings():  # noqa: F811, C901
    """Attaches VFS upload/download functions to the browser window."""

    if hasattr(js.window, "upload_file"):
        return

    def ensure_dir(path):
        if not path:
            return
        parts = path.split("/")
        current_path = ""
        for part in parts:
            if not part:
                continue
            current_path = current_path + "/"
            current_path += part if current_path else part
            try:
                os.mkdir(current_path)
            except OSError:
                pass

    def download_vfs_file(file_path):
        try:
            file_path = (
                os.path.normpath(file_path).lstrip("/").replace("../", "")
            )
            file_path = os.path.join(
                os.path.dirname(js.window.location.pathname),
                file_path,
            ).lstrip("/")

            file_path = os.path.join(os.getcwd(), file_path)

            # Check if the file exists in the VFS
            if not os.path.isfile(file_path):
                js.console.error(f"File not found: {file_path}")
                return

            with open(file_path, "rb") as f:
                content = f.read()
            b64_str = base64.b64encode(content).decode("utf-8")
            data_uri = "data:application/octet-stream;base64," + b64_str

            link = js.document.createElement("a")
            link.href = data_uri
            link.download = file_path.split("/")[-1]

            js.document.body.appendChild(link)
            link.click()
            js.document.body.removeChild(link)
        except Exception as e:
            js.console.error(f"Download failed for {file_path}: {e}")

    # --- NEW: Centralized File Processor ---
    def _process_files(
        files,
        target_filename,
        client_dest,
        server_dest,
        files_limit,
        total_size_limit,
        per_file_size_limit,
        allowed_extensions,
    ):
        num_files = files.length

        # 1. Validate File Count Limit
        if files_limit and num_files > files_limit:
            js.console.warn(
                f"Limit of {files_limit} files exceeded. Truncating."
            )
            num_files = files_limit

        # Safely convert JS arrays to Python lists (handles Pyodide JsProxy)
        if allowed_extensions and hasattr(allowed_extensions, "to_py"):
            allowed_extensions = allowed_extensions.to_py()

        total_size = 0

        for i in range(num_files):
            selected_file = files.item(i)

            # Only apply an override filename if it's a single file upload,
            # otherwise multiple files would overwrite each other!
            final_name = (
                target_filename
                if (target_filename and num_files == 1)
                else selected_file.name
            )

            # 2. Validate Extension
            if allowed_extensions:
                ext = (
                    selected_file.name.split(".")[-1].lower()
                    if "." in selected_file.name
                    else ""
                )
                if ext not in allowed_extensions:
                    js.console.error(
                        f"Skipped {selected_file.name}: "
                        + f"Extension '{ext}' not allowed."
                    )
                    continue

            # 3. Validate Per-File Size
            if (
                per_file_size_limit
                and selected_file.size > per_file_size_limit
            ):
                js.console.error(
                    f"Skipped {selected_file.name}: "
                    + f"Exceeds {per_file_size_limit} bytes."
                )
                continue

            # 4. Validate Total Size
            if total_size_limit:
                if (total_size + selected_file.size) > total_size_limit:
                    js.console.error(
                        f"Skipped {selected_file.name}: "
                        + "Exceeds total size limit."
                    )
                    continue
                total_size += selected_file.size

            # 5. Read and Save
            reader = js.window.FileReader.new()

            # Closure to lock in the correct filename AND file object
            # for the async callback
            def make_onload(fname, file_obj):
                def on_load(load_event):
                    array_buffer = load_event.target.result
                    uint8_array = js.Uint8Array.new(array_buffer)
                    file_bytes = bytes(uint8_array)

                    # 6. Hard limit size check (Security)
                    if len(file_bytes) > MAX_UPLOAD_SIZE:
                        js.console.error(
                            f"Upload rejected: '{fname}' exceeds the "
                            "hard limit of "
                            f"{MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB."
                        )
                        return

                    if client_dest:
                        # 7. Jail the path to VFS_UPLOAD_JAIL (Security)
                        raw_path = f"{client_dest.rstrip('/')}/{fname}"
                        safe_relative_path = raw_path.lstrip("/")

                        jail = os.path.abspath(VFS_UPLOAD_JAIL)
                        resolved_path = os.path.abspath(
                            os.path.join(jail, safe_relative_path)
                        )

                        jail_prefix = (
                            jail if jail.endswith("/") else jail + "/"
                        )
                        if not resolved_path.startswith(jail_prefix):
                            js.console.error(
                                f"Access denied: Attempted to upload"
                                f" '{fname}' outside of {jail}"
                            )
                            return

                        ensure_dir(os.path.dirname(resolved_path))
                        with open(resolved_path, "wb") as f:
                            f.write(file_bytes)
                        js.console.log(f"Uploaded to VFS: {resolved_path}")

                    if server_dest:
                        js.console.log(
                            f"Uploading {fname} to server destination:"
                            f" {server_dest}"
                        )

                        # Build standard multipart/form-data payload
                        form_data = js.window.FormData.new()
                        form_data.append("file", file_obj, fname)
                        form_data.append("server_destination", server_dest)

                        # js.eval is used here to safely build
                        # the JS object literal.
                        # This works flawlessly across both CPython/Pyodide
                        # and MicroPython FFI boundaries.
                        opts = js.eval("({method: 'POST'})")
                        opts.body = form_data

                        # POST to the current app endpoint.
                        # Your Pyplet backend will need a route handler
                        # to intercept POST requests here.
                        endpoint = js.window.location.pathname

                        promise = js.window.fetch(endpoint, opts)

                        def on_success(response):
                            # Pyodide proxies use getattr to safely
                            # check JS properties
                            if getattr(response, "ok", False):
                                js.console.log(
                                    f"Server upload complete: {fname}"
                                )
                            else:
                                js.console.error(
                                    f"Server upload failed for {fname}:"
                                    f" HTTP {response.status}"
                                )

                        def on_error(error):
                            js.console.error(
                                f"Server upload network error for {fname}:"
                                f" {error}"
                            )

                        promise.then(on_success).catch(on_error)

                return on_load

            # Pass both the resolved filename and the JS file object
            # into the closure
            reader.onload = make_onload(final_name, selected_file)
            reader.readAsArrayBuffer(selected_file)

    # --- Updated Handlers ---
    def upload_file(
        filename,
        client_dest,
        server_dest,
        files_limit,
        total_size_limit,
        per_file_size_limit,
        allowed_extensions,
    ):
        file_input = js.document.createElement("input")
        file_input.type = "file"

        # Native browser support for multiple files
        if files_limit is None or files_limit > 1:
            file_input.multiple = True

        # Native browser hint for extensions
        # (better UX before they even pick a file)
        if allowed_extensions:
            exts = (
                allowed_extensions.to_py()
                if hasattr(allowed_extensions, "to_py")
                else allowed_extensions
            )
            file_input.accept = ",".join(f".{ext}" for ext in exts)

        def on_change(event):
            if file_input.files.length > 0:
                _process_files(
                    file_input.files,
                    filename,
                    client_dest,
                    server_dest,
                    files_limit,
                    total_size_limit,
                    per_file_size_limit,
                    allowed_extensions,
                )

        file_input.addEventListener("change", on_change)
        file_input.click()

    def handle_click(
        event,
        client_dest,
        server_dest,
        files_limit,
        total_size_limit,
        per_file_size_limit,
        allowed_extensions,
    ):
        # Passes None for target_filename, relying on original file names
        upload_file(
            None,
            client_dest,
            server_dest,
            files_limit,
            total_size_limit,
            per_file_size_limit,
            allowed_extensions,
        )

    def handle_drop(
        event,
        client_dest,
        server_dest,
        files_limit,
        total_size_limit,
        per_file_size_limit,
        allowed_extensions,
    ):
        files = event.dataTransfer.files
        if files.length > 0:
            _process_files(
                files,
                None,
                client_dest,
                server_dest,
                files_limit,
                total_size_limit,
                per_file_size_limit,
                allowed_extensions,
            )

    # Expose to the global window
    js.window.download_vfs_file = download_vfs_file
    js.window.upload_file = upload_file
    js.window.handle_click = handle_click
    js.window.handle_drop = handle_drop


async def bootstrap_client(prefix, project_name, app_name, deps=()):
    global _apps
    _apps = prefix

    # Bind the VFS HTML helper to the browser window
    _setup_vfs_bindings()

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
