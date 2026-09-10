"""Imports ``pyplet.client`` under a MicroPython-shaped interpreter, so the
``except ImportError`` polyfill branch runs instead of the Pyodide one.
"""

import importlib
import sys
import types

import pytest

import pyplet
from tests import browser_stubs


def _micropython_implementation():
    """A ``sys.implementation`` clone naming MicroPython as the engine."""
    fields = dict(vars(sys.implementation))
    fields["name"] = "micropython"
    return types.SimpleNamespace(**fields)


def _js_with_deferred():
    """The browser stubs plus the JS promise factories the polyfill needs."""
    module = browser_stubs.make_js_module()
    module.create_deferred = lambda: types.SimpleNamespace(
        promise=types.SimpleNamespace(then=lambda callback: None),
        resolve=lambda value: None,
    )
    module.Promise = types.SimpleNamespace(
        resolve=lambda value: types.SimpleNamespace(then=lambda callback: None)
    )
    return module


@pytest.fixture
def imported(monkeypatch, capsys):
    """``pyplet.client`` freshly imported as MicroPython would import it,
    with whatever the import printed.
    """
    saved_module = sys.modules.pop("pyplet.client", None)
    saved_attribute = getattr(pyplet, "client", None)
    monkeypatch.setitem(sys.modules, "js", _js_with_deferred())
    monkeypatch.setattr(sys, "implementation", _micropython_implementation())
    try:
        client = importlib.import_module("pyplet.client")
        yield types.SimpleNamespace(
            client=client, stdout=capsys.readouterr().out
        )
    finally:
        sys.modules.pop("pyplet.client", None)
        if saved_module is not None:
            sys.modules["pyplet.client"] = saved_module
        if saved_attribute is not None:
            pyplet.client = saved_attribute
        elif hasattr(pyplet, "client"):
            delattr(pyplet, "client")


class TestMicroPythonPolyfill:
    def test_import_warns_and_installs_the_polyfill(self, imported):
        """The engine choice is announced and ``asyncio`` is the polyfill."""
        assert "falling back to MicroPython JS polyfill" in imported.stdout
        assert type(imported.client.asyncio).__name__ == "AsyncioPolyfill"

    def test_import_injects_the_deferred_helper(self, imported):
        """The JS deferred factory is defined through ``js.eval``."""
        sources = imported.client.js.eval.sources
        assert any("create_deferred" in source for source in sources)

    def test_unbounded_queue_gets_a_finite_micropython_maxlen(self, imported):
        """MicroPython needs a bound, so an unbounded queue defaults to 100."""
        queue = imported.client.asyncio.Queue(maxsize=0)
        assert queue._queue.maxlen == 100

    def test_sized_queue_keeps_its_own_bound(self, imported):
        """An explicit maxsize is passed straight to the deque."""
        assert imported.client.asyncio.Queue(maxsize=7)._queue.maxlen == 7

    def test_create_proxy_is_the_identity(self, imported):
        """MicroPython crosses the FFI natively, so no proxy is built."""
        target = object()
        assert imported.client.create_proxy(target) is target

    def test_create_task_drives_a_coroutine_to_completion(self, imported):
        """The task driver steps a coroutine and swallows StopIteration."""
        steps = []

        def coroutine():
            steps.append("ran")
            return
            yield

        imported.client.asyncio.create_task(coroutine())
        assert steps == ["ran"]

    def test_queue_put_then_get_round_trips(self, imported):
        """A queued item is returned without ever awaiting the JS promise."""
        queue = imported.client.asyncio.Queue()
        put = queue.put("payload")
        with pytest.raises(StopIteration):
            put.send(None)
        get = queue.get()
        with pytest.raises(StopIteration) as stop:
            get.send(None)
        assert stop.value.value == "payload"

    def test_create_task_hooks_a_yielded_js_promise(self, imported):
        """A coroutine yielding a thenable is resumed by that promise."""
        resumptions = []

        def coroutine():
            sent = yield types.SimpleNamespace(then=thenable)
            resumptions.append(sent)

        def thenable(step):
            resumptions.append("hooked")
            step("resumed")

        imported.client.asyncio.create_task(coroutine())
        assert resumptions == ["hooked", "resumed"]
