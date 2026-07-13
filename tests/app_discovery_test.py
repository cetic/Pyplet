"""
Regression tests for server-side application discovery in
pyplet.server._server.

`ServerApplication` subclasses register themselves into
`server_applications` via `__init_subclass__` when their module is loaded
by `_load_server_module`. Discovery must work no matter the shape of
`config.apps` (as set via `--apps`/`PYPLET_APPS`): a bare relative folder
name, a nested relative path, or an absolute path. Previously, discovery
was silently broken (imported the module but never registered it, or
failed to import at all) for anything other than a bare relative folder
name matching `config.apps` exactly.
"""

import glob
import sys

import pytest

from pyplet.server import _server

_SERVER_MODULE_TEMPLATE = """
from pyplet.server._server import ServerApplication


class {class_name}(ServerApplication):
    title = "{title}"
"""


def _write_app(apps_dir, project_name, app_name, class_name):
    project_dir = apps_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / f"{app_name}_server.py").write_text(
        _SERVER_MODULE_TEMPLATE.format(class_name=class_name, title=app_name)
    )


def _discover(apps_dir):
    """Mirror the discovery loop in `astart()` without booting a server."""
    for path in glob.glob(f"{apps_dir}/*/*_server.py"):
        _server._load_server_module(path)


@pytest.fixture
def clean_registry():
    """Snapshot/restore `server_applications` and `sys.modules` so
    discovery done by one test can't leak into another."""
    original_apps = dict(_server.server_applications)
    original_modules = set(sys.modules)

    yield

    _server.server_applications.clear()
    _server.server_applications.update(original_apps)
    for name in set(sys.modules) - original_modules:
        del sys.modules[name]


@pytest.mark.unit
class TestAppDiscovery:
    """Test suite for `_load_server_module` / `__init_subclass__`
    registration across different `config.apps` shapes."""

    def test_bare_relative_apps_dir(
        self, tmp_path, monkeypatch, clean_registry
    ):
        apps_dir = tmp_path / "apps"
        _write_app(apps_dir, "myproj", "myproj", "MyProjServer")

        monkeypatch.chdir(tmp_path)
        _discover("apps")

        assert ("myproj", "myproj") in _server.server_applications

    def test_nested_relative_apps_dir(
        self, tmp_path, monkeypatch, clean_registry
    ):
        """A `config.apps` value with a path separator (e.g. "sub/apps")
        used to break registration: the dotted module name derived from
        it had more than 3 components, so `__init_subclass__`'s
        `len(qualname) == 3` check silently rejected it."""
        apps_dir = tmp_path / "sub" / "apps"
        _write_app(apps_dir, "myproj", "myproj", "MyProjServer")

        monkeypatch.chdir(tmp_path)
        _discover("sub/apps")

        assert ("myproj", "myproj") in _server.server_applications

    def test_absolute_apps_dir(self, tmp_path, clean_registry):
        """An absolute `config.apps` path used to raise a `TypeError`
        from `import_module` (a leading path separator produces a
        leading dot in the dotted module name, i.e. an invalid relative
        import), so no apps were ever loaded."""
        apps_dir = tmp_path / "myapps"
        _write_app(apps_dir, "myproj", "myproj", "MyProjServer")

        _discover(str(apps_dir))

        assert ("myproj", "myproj") in _server.server_applications

    def test_multiple_apps_under_one_project(
        self, tmp_path, monkeypatch, clean_registry
    ):
        apps_dir = tmp_path / "apps"
        _write_app(apps_dir, "myproj", "one", "OneServer")
        _write_app(apps_dir, "myproj", "two", "TwoServer")

        monkeypatch.chdir(tmp_path)
        _discover("apps")

        assert ("myproj", "one") in _server.server_applications
        assert ("myproj", "two") in _server.server_applications

    def test_relative_import_between_sibling_apps(
        self, tmp_path, monkeypatch, clean_registry
    ):
        """Regression test: an app module doing an ordinary intra-project
        relative import (e.g. `from . import chat_server`, as a
        dashboard app might do to reuse another app's server class)
        used to raise `ModuleNotFoundError: No module named
        '_pyplet_apps'`, because the synthetic package hierarchy was
        never actually registered in `sys.modules` — only the leaf
        module was."""
        apps_dir = tmp_path / "apps"
        _write_app(apps_dir, "examples", "chat", "ChatServer")
        (apps_dir / "examples" / "dashboard_server.py").write_text(
            "from . import chat_server\n"
            "from pyplet.server._server import ServerApplication\n"
            "\n\n"
            "class DashboardServer(ServerApplication):\n"
            '    title = "dashboard"\n'
        )

        monkeypatch.chdir(tmp_path)
        # Load the app with the relative import first, so it can't rely
        # on its sibling already being in sys.modules.
        paths = sorted(
            glob.glob("apps/*/*_server.py"), key=lambda p: "dashboard" not in p
        )
        for path in paths:
            _server._load_server_module(path)

        assert ("examples", "chat") in _server.server_applications
        assert ("examples", "dashboard") in _server.server_applications

    def test_reused_relative_apps_name_across_different_cwd(
        self, tmp_path, monkeypatch, clean_registry
    ):
        """Regression test: Python's import machinery caches a finder
        per directory *string* in `sys.path_importer_cache`. Using a
        relative path there means the same literal string (e.g. bare
        "apps") reused under a different cwd — across two projects, or
        across a server restart — would return a stale finder for the
        wrong (or now-gone) directory. `_load_server_module` must
        resolve to an absolute path before registering it as a
        package's `__path__`."""
        first_root = tmp_path / "first"
        _write_app(first_root / "apps", "myproj", "myproj", "MyProjServer")
        monkeypatch.chdir(first_root)
        _discover("apps")
        assert ("myproj", "myproj") in _server.server_applications

        second_root = tmp_path / "second"
        _write_app(second_root / "apps", "other", "other", "OtherServer")
        monkeypatch.chdir(second_root)
        _discover("apps")

        assert ("other", "other") in _server.server_applications
