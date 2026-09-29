"""Executes ``pyplet.client.bootstrap_client`` under plain CPython, on
both engine paths, against plain-object stand-ins for the browser.
"""

import asyncio
import sys
import types

import pytest

from tests import browser_stubs

_PREFIX = "fake_apps"
_PROJECT = "proj"
_APP = "myapp"
_MODULE = f"{_PREFIX}.{_PROJECT}.{_APP}_client"
_SPLASH_ID = "pyplet-boot-splash"


@pytest.fixture
def client_module(monkeypatch):
    yield from browser_stubs.fresh_client(monkeypatch)


def _app_class(client, module_name, hooks):
    """Builds a ``ClientApplication`` subclass carrying the named hooks."""

    def __init__(self):
        self.inits = 0
        self.sockets = []

    async def client_init(self):
        self.inits += 1

    async def websocket_client_loop(self, ws):
        self.sockets.append(ws)

    namespace = {"__module__": module_name, "__init__": __init__}
    if "init" in hooks:
        namespace["client_init"] = client_init
    if "loop" in hooks:
        namespace["websocket_client_loop"] = websocket_client_loop
    return type("SpyApp", (client.ClientApplication,), namespace)


def _self_registering_app(client, monkeypatch, hooks=("init",)):
    """Defines the app class the way its module does at import time."""
    monkeypatch.setattr(client, "_apps", _PREFIX)
    _app_class(client, _MODULE, hooks)
    return client.client_applications[_PROJECT, _APP]


def _app_module(monkeypatch, **attributes):
    """Registers the module ``bootstrap_client`` will import."""
    module = types.ModuleType(_MODULE)
    for name, value in attributes.items():
        setattr(module, name, value)
    monkeypatch.setitem(sys.modules, _MODULE, module)
    return module


def _fake_micropip(monkeypatch, recorder):
    """A ``micropip`` whose async ``install`` records its argument."""
    module = types.ModuleType("micropip")

    async def install(packages):
        recorder.append(packages)

    module.install = install
    monkeypatch.setitem(sys.modules, "micropip", module)
    return module


class TestApplicationLookup:
    @pytest.mark.asyncio
    async def test_the_registry_entry_is_reused_as_is(self, client_module, monkeypatch):
        registered = _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert client_module.client_applications[_PROJECT, _APP] is (registered), (
            "__init_subclass__ already instantiated the app: bootstrap must "
            "reuse that instance rather than build a second one"
        )
        assert registered.inits == 1

    @pytest.mark.asyncio
    async def test_an_unregistered_class_is_found_by_scanning_the_module(
        self, client_module, monkeypatch
    ):
        scanned = _app_class(client_module, "elsewhere.mod", ("init",))
        _app_module(monkeypatch, SpyApp=scanned)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        instance = client_module.client_applications[_PROJECT, _APP]
        assert isinstance(instance, scanned), (
            "MicroPython does not run __init_subclass__ registration for "
            "the app module, so bootstrap must scan the module itself"
        )
        assert instance.inits == 1

    @pytest.mark.asyncio
    async def test_the_base_class_alone_is_not_an_application(
        self, client_module, monkeypatch
    ):
        _app_module(monkeypatch, ClientApplication=client_module.ClientApplication)

        with pytest.raises(RuntimeError, match="Could not find a Client"):
            await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

    @pytest.mark.asyncio
    async def test_a_module_without_an_application_raises(
        self, client_module, monkeypatch
    ):
        _app_module(monkeypatch)

        with pytest.raises(RuntimeError, match=f"subclass in {_PROJECT}/{_APP}"):
            await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)


class TestBootstrapWiring:
    @pytest.mark.asyncio
    async def test_the_vfs_helpers_are_bound_before_the_app_loads(
        self, client_module, monkeypatch
    ):
        _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        window = client_module.js.window
        for name in ("download_vfs_file", "upload_file", "handle_drop"):
            assert callable(getattr(window, name, None)), (
                f"window.{name} must exist after bootstrap: the served HTML "
                "carries inline handlers calling it"
            )

    @pytest.mark.asyncio
    async def test_an_overridden_client_init_is_awaited(
        self, client_module, monkeypatch
    ):
        app = _self_registering_app(client_module, monkeypatch, ("init",))
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert app.inits == 1

    @pytest.mark.asyncio
    async def test_the_base_client_init_is_not_awaited(
        self, client_module, monkeypatch
    ):
        calls = []

        async def spy(self):
            calls.append(self)

        monkeypatch.setattr(client_module.ClientApplication, "client_init", spy)
        _self_registering_app(client_module, monkeypatch, ())
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert calls == [], (
            "an app that declares no client_init must not have the base "
            "no-op awaited on its behalf"
        )

    @pytest.mark.asyncio
    async def test_the_boot_splash_is_dropped(self, client_module, monkeypatch):
        _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)
        splash = browser_stubs.FakeElement("div")
        client_module.js.document.elements_by_id[_SPLASH_ID] = splash

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert splash.removals == 1

    @pytest.mark.asyncio
    async def test_an_already_gone_splash_is_tolerated(
        self, client_module, monkeypatch
    ):
        app = _self_registering_app(client_module, monkeypatch, ("init",))
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert client_module.js.document.elements_by_id == {}
        assert app.inits == 1


class TestWebsocketWiring:
    @pytest.mark.asyncio
    async def test_the_app_socket_is_opened_and_driven_on_open(
        self, client_module, monkeypatch
    ):
        app = _self_registering_app(client_module, monkeypatch, ("loop",))
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert len(client_module.WebSocket.instances) == 1
        socket = client_module.WebSocket.instances[0]
        assert socket.url == f"/apps/{_PROJECT}/{_APP}.ws"
        assert callable(socket.onmessage)
        assert callable(socket.onclose)
        assert app.sockets == [], (
            "the loop must wait for the JS open event, not run at bootstrap"
        )

        socket.onopen(None)
        await asyncio.sleep(0)

        assert len(app.sockets) == 1
        wrapper = app.sockets[0]
        assert isinstance(wrapper, client_module.ClientWebSocket)
        assert wrapper.ws is socket

    @pytest.mark.asyncio
    async def test_no_socket_is_opened_without_a_loop(self, client_module, monkeypatch):
        _self_registering_app(client_module, monkeypatch, ("init",))
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert client_module.WebSocket.instances == [], (
            "an app that declares no websocket_client_loop must not open a "
            "socket the server has no handler for"
        )


class TestDependencyInstall:
    @pytest.mark.asyncio
    async def test_pyodide_installs_the_deps_with_micropip(
        self, client_module, monkeypatch
    ):
        installed = []
        _fake_micropip(monkeypatch, installed)
        _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)

        await client_module.bootstrap_client(
            _PREFIX, _PROJECT, _APP, deps=("numpy", "matplotlib")
        )

        assert installed == [["numpy", "matplotlib"]]

    @pytest.mark.asyncio
    async def test_a_missing_micropip_is_pulled_in_and_retried(
        self, client_module, monkeypatch
    ):
        installed = []
        loaded = []
        monkeypatch.setitem(sys.modules, "micropip", None)
        pyodide_js = types.ModuleType("pyodide_js")

        async def load_package(name):
            loaded.append(name)
            _fake_micropip(monkeypatch, installed)

        pyodide_js.loadPackage = load_package
        monkeypatch.setitem(sys.modules, "pyodide_js", pyodide_js)
        _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP, deps=("numpy",))

        assert loaded == ["micropip"], (
            "a stale PyScript cache can leave micropip unregistered: "
            "bootstrap must reload it through the Pyodide JS API"
        )
        assert installed == [["numpy"]]

    @pytest.mark.asyncio
    async def test_micropython_installs_the_deps_with_mip(
        self, client_module, monkeypatch
    ):
        installed = []
        mip = types.ModuleType("mip")
        mip.install = installed.append
        monkeypatch.setitem(sys.modules, "mip", mip)
        _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)

        with monkeypatch.context() as engine:
            engine.setattr(sys.implementation, "name", "micropython")
            await client_module.bootstrap_client(
                _PREFIX, _PROJECT, _APP, deps=("numpy", "requests")
            )

        assert installed == ["numpy", "requests"], (
            "MicroPython has no micropip: deps go through mip, one call per package"
        )

    @pytest.mark.asyncio
    async def test_an_app_without_deps_installs_nothing(
        self, client_module, monkeypatch
    ):
        installed = []
        _fake_micropip(monkeypatch, installed)
        _self_registering_app(client_module, monkeypatch)
        _app_module(monkeypatch)

        await client_module.bootstrap_client(_PREFIX, _PROJECT, _APP)

        assert installed == []
