"""Plain-object stand-ins for the browser globals ``pyplet.client`` binds
to, plus a fixture body importing that module fresh against them.
"""

import importlib
import sys
import types

import pyplet


class FakeConsole:
    """``js.console``: keeps every message the client emits."""

    def __init__(self):
        self.logs = []
        self.warnings = []
        self.errors = []

    def log(self, message):
        self.logs.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def error(self, message):
        self.errors.append(message)


class FakeFactory:
    """A JS constructor: ``new()`` builds one product and records it."""

    def __init__(self, product):
        self.product = product
        self.instances = []

    def new(self, *args):
        instance = self.product(*args)
        self.instances.append(instance)
        return instance


class FakeJsProxy:
    """A Pyodide ``JsProxy``: unusable from Python until ``to_py()``."""

    def __init__(self, value):
        self._value = value
        self.to_py_calls = 0

    def to_py(self):
        self.to_py_calls += 1
        return self._value

    def __bool__(self):
        return bool(self._value)


class FakeFile:
    """A ``File`` entry: a name, a size and the bytes a reader yields."""

    def __init__(self, name, content=b"", size=None):
        self.name = name
        self.content = content
        self.size = len(content) if size is None else size


class FakeFileList:
    """A ``FileList``: ``length`` plus ``item(i)``, as the DOM exposes it."""

    def __init__(self, files=()):
        self._files = list(files)
        self.length = len(self._files)

    def item(self, index):
        return self._files[index]


class FakeFileReader:
    """A ``FileReader`` firing ``onload`` synchronously on read."""

    def __init__(self):
        self.onload = None
        self.read_files = []

    def readAsArrayBuffer(self, file_obj):
        self.read_files.append(file_obj)
        if self.onload is not None:
            target = types.SimpleNamespace(result=file_obj.content)
            self.onload(types.SimpleNamespace(target=target))


class FakeFormData:
    """A ``FormData``: the appended tuples, in order."""

    def __init__(self):
        self.entries = []

    def append(self, *args):
        self.entries.append(args)


class FakePromise:
    """``fetch``'s promise, settled synchronously one way or the other."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def then(self, callback):
        if self.error is None:
            callback(self.response)
        return self

    def catch(self, callback):
        if self.error is not None:
            callback(self.error)
        return self


class FakeWebSocket:
    """The JS ``WebSocket``: a url, the handlers set on it, what was sent."""

    def __init__(self, url):
        self.url = url
        self.sent = []
        self.onopen = None
        self.onmessage = None
        self.onclose = None

    def send(self, message):
        self.sent.append(message)


class FakeElement:
    """A DOM element: an attribute bag counting clicks and removals."""

    def __init__(self, tag):
        self.tag = tag
        self.clicks = 0
        self.removals = 0
        self.listeners = {}

    def addEventListener(self, name, callback):
        self.listeners[name] = callback

    def click(self):
        self.clicks += 1

    def remove(self):
        self.removals += 1


class FakeFileInput(FakeElement):
    """The upload ``<input>``: ``click()`` stands for the user picking."""

    def __init__(self, tag, files):
        super().__init__(tag)
        self.files = files

    def click(self):
        self.clicks += 1
        callback = self.listeners.get("change")
        if callback is not None:
            callback(types.SimpleNamespace(type="change"))


class FakeBody:
    """``document.body``: what got appended to it, and detached from it."""

    def __init__(self):
        self.appended = []
        self.removed = []

    def appendChild(self, element):
        self.appended.append(element)

    def removeChild(self, element):
        self.removed.append(element)


class FakeDocument:
    """``js.document``: element creation, ``body`` and lookups by id."""

    def __init__(self, picked_files=None, elements_by_id=None):
        self.picked_files = (
            FakeFileList() if picked_files is None else picked_files
        )
        self.elements_by_id = dict(elements_by_id or {})
        self.body = FakeBody()
        self.created = []
        self.create_error = None

    def createElement(self, tag):
        if self.create_error is not None:
            raise self.create_error
        if tag == "input":
            element = FakeFileInput(tag, self.picked_files)
        else:
            element = FakeElement(tag)
        self.created.append(element)
        return element

    def getElementById(self, element_id):
        return self.elements_by_id.get(element_id)


class FakeEval:
    """``js.eval``: records sources, answers the client's object literal."""

    def __init__(self):
        self.sources = []

    def __call__(self, source):
        self.sources.append(source)
        if source.strip().startswith("({"):
            return types.SimpleNamespace(method="POST")
        return None


class FakeWindow:
    """``js.window``: no auto-created attributes, so ``hasattr`` is real."""

    def __init__(self, pathname="/apps/proj/myapp"):
        self.location = types.SimpleNamespace(pathname=pathname)
        self.FileReader = FakeFactory(FakeFileReader)
        self.FormData = FakeFactory(FakeFormData)
        self.fetch_calls = []
        self.fetch_result = FakePromise(
            response=types.SimpleNamespace(ok=True, status=200)
        )

    def fetch(self, endpoint, options):
        self.fetch_calls.append((endpoint, options))
        return self.fetch_result


def make_js_module(pathname="/apps/proj/myapp", picked_files=None, ids=None):
    """Builds the fake ``js`` module the client imports."""
    module = types.ModuleType("js")
    module.window = FakeWindow(pathname)
    module.document = FakeDocument(picked_files, ids)
    module.console = FakeConsole()
    module.eval = FakeEval()
    module.Uint8Array = FakeFactory(bytes)
    module.WebSocket = FakeFactory(FakeWebSocket)
    return module


def fresh_client(monkeypatch, **kwargs):
    """Fixture body: imports ``pyplet.client`` fresh, then unimports it,
    so its ``_apps`` and ``client_applications`` never leak between tests.
    """
    saved_module = sys.modules.pop("pyplet.client", None)
    saved_attribute = getattr(pyplet, "client", None)
    monkeypatch.setitem(sys.modules, "js", make_js_module(**kwargs))
    try:
        yield importlib.import_module("pyplet.client")
    finally:
        sys.modules.pop("pyplet.client", None)
        if saved_module is not None:
            sys.modules["pyplet.client"] = saved_module
        if saved_attribute is not None:
            pyplet.client = saved_attribute
        elif hasattr(pyplet, "client"):
            delattr(pyplet, "client")
