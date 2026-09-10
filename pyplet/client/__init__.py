import base64
import collections
import os
import sys
from importlib import import_module

import js
from js import WebSocket

try:
    if sys.implementation.name == "micropython":
        raise ImportError("asyncio Queue are not available on MicroPython")

    # 1. Try Pyodide / CPython standard library
    import asyncio

    try:
        from pyodide.ffi import create_proxy
    except ImportError:

        def create_proxy(x):
            return x

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
    def create_proxy(x):
        return x


import pyplet

VFS_UPLOAD_JAIL = "/vfs_uploads"
SERVER_UPLOAD_JAIL = "server_uploads"
MAX_UPLOAD_SIZE = 50 * 2**20  # 50 MiB

_apps = None
client_applications: dict[tuple[str, str], "ClientApplication"] = {}


def _ensure_dir(path):
    """Create every missing parent directory of a VFS path."""
    if not path:
        return
    parts = path.split("/")
    current_path = ""
    for part in parts:
        if not part:
            continue
        current_path = current_path + "/"
        current_path += part if current_path else part
        try:  # noqa: SIM105
            os.mkdir(current_path)
        except OSError:
            pass


def download_vfs_file(file_path):
    """Hand the browser a VFS file as a base64 data-URI download."""
    try:
        file_path = os.path.normpath(file_path).lstrip("/").replace("../", "")
        file_path = os.path.join(
            os.path.dirname(js.window.location.pathname),
            file_path,
        ).lstrip("/")

        file_path = os.path.join(os.getcwd(), file_path)

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


def _read_uploaded_bytes(load_event):
    """Turn a FileReader load event into Python bytes."""
    array_buffer = load_event.target.result
    uint8_array = js.Uint8Array.new(array_buffer)
    return bytes(uint8_array)


def _write_upload_to_vfs(fname, file_bytes, client_dest):
    """Write an upload inside the VFS jail; False when the path escapes."""
    raw_path = f"{client_dest.rstrip('/')}/{fname}"
    safe_relative_path = raw_path.lstrip("/")

    jail = os.path.abspath(VFS_UPLOAD_JAIL)
    resolved_path = os.path.abspath(os.path.join(jail, safe_relative_path))

    jail_prefix = jail if jail.endswith("/") else jail + "/"
    if not resolved_path.startswith(jail_prefix):
        js.console.error(
            f"Access denied: Attempted to upload '{fname}' outside of {jail}"
        )
        return False

    _ensure_dir(os.path.dirname(resolved_path))
    with open(resolved_path, "wb") as f:
        f.write(file_bytes)
    js.console.log(f"Uploaded to VFS: {resolved_path}")
    return True


def _post_upload_to_server(fname, file_obj, server_dest):
    """POST an upload to the server destination of the current app."""
    js.console.log(f"Uploading {fname} to server destination: {server_dest}")

    form_data = js.window.FormData.new()
    form_data.append("file", file_obj, fname)
    form_data.append("server_destination", server_dest)

    opts = js.eval("({method: 'POST'})")
    opts.body = form_data

    endpoint = js.window.location.pathname
    promise = js.window.fetch(endpoint, opts)

    def on_success(response):
        if getattr(response, "ok", False):
            js.console.log(f"Server upload complete: {fname}")
        else:
            js.console.error(
                f"Server upload failed for {fname}: HTTP {response.status}"
            )

    def on_error(error):
        js.console.error(f"Server upload network error for {fname}: {error}")

    promise.then(on_success).catch(on_error)


def _make_upload_onload(fname, file_obj, client_dest, server_dest):
    """Build the FileReader callback that stores one uploaded file."""

    def on_load(load_event):
        file_bytes = _read_uploaded_bytes(load_event)

        if len(file_bytes) > MAX_UPLOAD_SIZE:
            js.console.error(
                f"Upload rejected: '{fname}' exceeds the "
                "hard limit of "
                f"{MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB."
            )
            return

        if client_dest and not _write_upload_to_vfs(
            fname, file_bytes, client_dest
        ):
            return

        if server_dest:
            _post_upload_to_server(fname, file_obj, server_dest)

    return on_load


def _total_size_rejected(selected_file, total_size, total_size_limit):
    """Tell whether a file busts the batch total-size limit."""
    if (total_size + selected_file.size) > total_size_limit:
        js.console.error(
            f"Skipped {selected_file.name}: " + "Exceeds total size limit."
        )
        return True
    return False


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
    """Validate a batch of picked files, then store each accepted one."""
    num_files = _capped_file_count(files.length, files_limit)
    allowed_extensions = _as_extension_list(allowed_extensions)

    total_size = 0

    for i in range(num_files):
        selected_file = files.item(i)

        final_name = (
            target_filename
            if (target_filename and num_files == 1)
            else selected_file.name
        )

        if _extension_rejected(selected_file, allowed_extensions):
            continue

        if _per_file_size_rejected(selected_file, per_file_size_limit):
            continue

        if total_size_limit:
            if _total_size_rejected(
                selected_file, total_size, total_size_limit
            ):
                continue
            total_size += selected_file.size

        reader = js.window.FileReader.new()
        reader.onload = _make_upload_onload(
            final_name, selected_file, client_dest, server_dest
        )
        reader.readAsArrayBuffer(selected_file)


def _make_change_handler(
    file_input,
    filename,
    client_dest,
    server_dest,
    files_limit,
    total_size_limit,
    per_file_size_limit,
    allowed_extensions,
):
    """Build the listener processing what the file dialog picked."""

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

    return on_change


def upload_file(
    filename,
    client_dest,
    server_dest,
    files_limit,
    total_size_limit,
    per_file_size_limit,
    allowed_extensions,
):
    """Open the browser file dialog and process the picked files."""
    file_input = js.document.createElement("input")
    file_input.type = "file"

    if files_limit is None or files_limit > 1:
        file_input.multiple = True

    if allowed_extensions:
        exts = (
            allowed_extensions.to_py()
            if hasattr(allowed_extensions, "to_py")
            else allowed_extensions
        )
        file_input.accept = ",".join(f".{ext}" for ext in exts)

    file_input.addEventListener(
        "change",
        _make_change_handler(
            file_input,
            filename,
            client_dest,
            server_dest,
            files_limit,
            total_size_limit,
            per_file_size_limit,
            allowed_extensions,
        ),
    )
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
    """Open the upload dialog, keeping each file's original name."""
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
    """Process the files carried by a drag-and-drop event."""
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


def _setup_vfs_bindings():
    """Attaches VFS upload/download functions to the browser window."""

    if hasattr(js.window, "upload_file"):
        return

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
            try:
                import micropip
            except ModuleNotFoundError:
                # micropip ships with Pyodide, but a reload after the app has
                # already been used can restore a partial/inconsistent Pyodide
                # package set from PyScript's IndexedDB cache (@pyscript.fs +
                # the pyodide package cache), leaving micropip unregistered so
                # `import micropip` raises ModuleNotFoundError at boot. Recover
                # exactly as the error message itself advises: pull the package
                # in via the Pyodide JS API and retry. This self-heals a stale
                # or dirty cache without forcing the user to clear IndexedDB.
                import pyodide_js

                await pyodide_js.loadPackage("micropip")
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
        found_class = _find_client_application(mod, project_name, app_name)

        # Instantiate it and manually register it
        client_application = found_class()
        client_applications[project_name, app_name] = client_application

    if (
        client_application.__class__.client_init
        is not ClientApplication.client_init
    ):
        await client_application.client_init()

    # Drop the boot splash (server-rendered into #container) now that the app
    # module has loaded and any client_init UI has mounted. Apps that replace
    # #container's contents already removed it; this by-id removal also covers
    # apps that append to #container, so the spinner never lingers. Gate on
    # truthiness — getElementById yields a falsy JS null when already gone.
    _drop_boot_splash()

    if (
        client_application.__class__.websocket_client_loop
        is not ClientApplication.websocket_client_loop
    ):
        ws = WebSocket.new(f"/apps/{project_name}/{app_name}.ws")
        ws_wrapper = ClientWebSocket(ws)
        gen = client_application.websocket_client_loop(ws_wrapper)

        # Use our driver to trigger the loop when JS says the socket is open
        ws.onopen = create_proxy(lambda event: asyncio.create_task(gen))


def _drop_boot_splash():
    """Remove the boot splash once the app UI has mounted."""
    splash = js.document.getElementById("pyplet-boot-splash")
    if splash:
        splash.remove()


def _capped_file_count(num_files, files_limit):
    """Cap an incoming file count to the configured limit."""
    if files_limit and num_files > files_limit:
        js.console.warn(f"Limit of {files_limit} files exceeded. Truncating.")
        return files_limit
    return num_files


def _as_extension_list(allowed_extensions):
    """Normalise a JS or Python extension list to a Python list."""
    if allowed_extensions and hasattr(allowed_extensions, "to_py"):
        return allowed_extensions.to_py()
    return allowed_extensions


def _extension_rejected(selected_file, allowed_extensions):
    """Tell whether a file is barred by the allowed-extension list."""
    if not allowed_extensions:
        return False
    name = selected_file.name
    ext = name.split(".")[-1].lower() if "." in name else ""
    if ext not in allowed_extensions:
        js.console.error(
            f"Skipped {name}: " + f"Extension '{ext}' not allowed."
        )
        return True
    return False


def _find_client_application(mod, project_name, app_name):
    """Return the ClientApplication subclass declared by an app module."""
    for item_name in dir(mod):
        item = getattr(mod, item_name)
        if (
            isinstance(item, type)
            and issubclass(item, ClientApplication)
            and item is not ClientApplication
        ):
            return item
    raise RuntimeError(
        "Could not find a ClientApplication "
        f"subclass in {project_name}/{app_name}"
    )


def _per_file_size_rejected(selected_file, per_file_size_limit):
    """Tell whether a file busts the per-file size limit."""
    if per_file_size_limit and selected_file.size > per_file_size_limit:
        js.console.error(
            f"Skipped {selected_file.name}: "
            + f"Exceeds {per_file_size_limit} bytes."
        )
        return True
    return False


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
