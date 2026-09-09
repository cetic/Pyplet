"""Flat apps-root layout (``pyplet.server._apps``): discovery, registration,
the index/ACL listings, ``package()``'s VFS keys and the ``static/`` root.
"""

import gzip
import json
import os
import sys
import tempfile

import pytest
from pyplet.server import _apps, _server, oauth, templates
from pyplet.server._server import _app_spec
from pyplet.server.config import config
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

_SERVER_MODULE_TEMPLATE = """
from pyplet.server._server import ServerApplication


class {class_name}(ServerApplication):
    title = "{title}"
"""


def _write_flat_app(root, app_name, class_name):
    """Write ``<root>/<app>_server.py`` + ``<app>_client.py`` (flat)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{app_name}_server.py").write_text(
        _SERVER_MODULE_TEMPLATE.format(class_name=class_name, title=app_name)
    )
    (root / f"{app_name}_client.py").write_text("# client\n")


def _write_nested_app(apps_dir, project, app_name, class_name):
    """Write ``<apps_dir>/<project>/<app>_server.py`` + client (nested)."""
    _write_flat_app(apps_dir / project, app_name, class_name)


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
class TestFlatLayoutDiscovery:
    """`_apps` must read a flat root, a nested root, and a mixed one."""

    def test_flat_root_uses_its_own_basename_as_project(
        self, tmp_path, preserve_config_dict
    ):
        """The reported bug: `PYPLET_APPS=.../examples` found nothing."""
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        config.apps = str(root)

        assert _apps.server_modules() == [
            ("examples", "chat", root / "chat_server.py")
        ]
        assert _apps.client_apps() == [("examples", "chat")]

    def test_flat_root_spelled_dot_still_names_the_project(
        self, tmp_path, monkeypatch, preserve_config_dict
    ):
        """`PYPLET_APPS=.` must resolve before taking the basename —
        `Path(".").name` is the empty string, which would produce an
        unroutable `/apps//chat` URL."""
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        monkeypatch.chdir(root)
        config.apps = "."

        assert _apps.client_apps() == [("examples", "chat")]

    def test_nested_root_is_unchanged(self, tmp_path, preserve_config_dict):
        apps_dir = tmp_path / "apps"
        _write_nested_app(apps_dir, "myproj", "one", "OneServer")
        config.apps = str(apps_dir)

        assert _apps.client_apps() == [("myproj", "one")]

    def test_mixed_root_yields_both_layouts(
        self, tmp_path, preserve_config_dict
    ):
        """A root holding app files AND project subdirectories must not
        make one layout hide the other."""
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        _write_nested_app(root, "extras", "extra", "ExtraServer")
        config.apps = str(root)

        assert _apps.client_apps() == [
            ("examples", "chat"),
            ("extras", "extra"),
        ]

    def test_dot_directories_are_not_discovered(
        self, tmp_path, preserve_config_dict
    ):
        """`glob` skips dot-prefixed entries, keeping `.transpiled/` out."""
        root = tmp_path / "examples"
        _write_flat_app(root / ".transpiled", "ghost", "GhostServer")
        _write_nested_app(root, ".cache", "stale", "StaleServer")
        config.apps = str(root)

        assert _apps.server_modules() == []
        assert _apps.client_apps() == []

    def test_subdirectory_of_the_same_name_wins(
        self, tmp_path, caplog, preserve_config_dict
    ):
        """The nested project owns the name — it is the one `project_dir`
        can address — so the flat apps are skipped, loudly.
        """
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        _write_nested_app(root, "examples", "nested", "NestedServer")
        config.apps = str(root)

        assert _apps.flat_project() is None
        assert _apps.client_apps() == [("examples", "nested")]
        assert "already claims that project name" in caplog.text

    def test_unroutable_flat_root_name_is_reported(
        self, tmp_path, caplog, preserve_config_dict
    ):
        """The route regex only accepts identifier-shaped projects, so a
        root named e.g. `my-examples` would be discovered and then 404.
        Discovery still returns it; the warning explains the 404."""
        root = tmp_path / "my-examples"
        _write_flat_app(root, "chat", "ChatServer")
        config.apps = str(root)

        assert _apps.flat_project() == "my-examples"
        assert "not a valid project name" in caplog.text

    def test_empty_root_finds_nothing(self, tmp_path, preserve_config_dict):
        root = tmp_path / "empty"
        root.mkdir()
        config.apps = str(root)

        assert _apps.flat_project() is None
        assert _apps.server_modules() == []

    def test_missing_root_finds_nothing(self, tmp_path, preserve_config_dict):
        config.apps = str(tmp_path / "does_not_exist")

        assert _apps.flat_project() is None
        assert _apps.client_apps() == []

    def test_project_dir_maps_both_layouts(
        self, tmp_path, preserve_config_dict
    ):
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        _write_nested_app(root, "extras", "extra", "ExtraServer")
        config.apps = str(root)

        assert _apps.project_dir("examples") == root
        assert _apps.project_dir("extras") == root / "extras"


@pytest.mark.unit
class TestFlatLayoutRegistration:
    """A flat app must actually register under the flat project name."""

    def test_flat_app_registers_under_the_root_basename(
        self, tmp_path, preserve_config_dict, clean_registry
    ):
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        config.apps = str(root)

        for project, _app, path in _apps.server_modules():
            _server._load_server_module(str(path), project=project)

        assert ("examples", "chat") in _server.server_applications

    def test_flat_root_spelled_dot_registers_a_named_project(
        self, tmp_path, monkeypatch, preserve_config_dict, clean_registry
    ):
        """Without the explicit project name, `_load_server_module` would
        fall back to the *unresolved* parent's name — empty for "."."""
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        monkeypatch.chdir(root)
        config.apps = "."

        for project, _app, path in _apps.server_modules():
            _server._load_server_module(str(path), project=project)

        assert ("examples", "chat") in _server.server_applications


@pytest.mark.unit
class TestFlatLayoutListings:
    """The index page and the ACL filter must see the same apps."""

    def test_permitted_apps_covers_the_flat_layout(
        self, tmp_path, monkeypatch, preserve_config_dict
    ):
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        _write_flat_app(root, "secret", "SecretServer")
        config.apps = str(root)

        monkeypatch.setattr(
            oauth,
            "is_app_permitted",
            lambda project, app, email: app != "secret",
        )

        assert oauth.permitted_apps("someone@example.com") == [
            ("examples", "chat")
        ]

    def test_index_lists_a_flat_app_when_auth_is_disabled(
        self, tmp_path, monkeypatch, preserve_config_dict
    ):
        """The reported symptom: an index page claiming no apps installed."""
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        config.apps = str(root)
        monkeypatch.setattr(oauth, "auth_enabled", lambda: False)

        page = str(templates.index_template(None))

        assert 'href="apps/examples/chat"' in page
        assert "No applications have been installed yet." not in page


@pytest.mark.unit
class TestFlatLayoutPackaging:
    """`package()`'s VFS keys stay ``apps/<project>/<file>`` when flat: the
    browser imports from them, so the on-disk shape must not leak.
    """

    def test_flat_app_vfs_keys(self, tmp_path, preserve_config_dict):
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        config.apps = str(root)

        handler = _FakeHandler("examples", "chat")
        _server.ServerApplication().package(handler)
        file_map = json.loads(gzip.decompress(handler.body).decode("utf-8"))

        assert "apps/examples/chat_server.py" in file_map
        assert "apps/examples/chat_client.py" in file_map
        assert not any(k.startswith("/") for k in file_map)
        assert not any(k.startswith(str(tmp_path)) for k in file_map)

    def test_flat_app_static_dir_is_excluded_from_the_bundle(
        self, tmp_path, preserve_config_dict
    ):
        """Static assets are served over HTTP, not shipped in the VFS."""
        root = tmp_path / "examples"
        _write_flat_app(root, "chat", "ChatServer")
        (root / "static").mkdir()
        (root / "static" / "big.js").write_text("// served, not bundled\n")
        config.apps = str(root)

        handler = _FakeHandler("examples", "chat")
        _server.ServerApplication().package(handler)
        file_map = json.loads(gzip.decompress(handler.body).decode("utf-8"))

        assert not any("static/big.js" in k for k in file_map)


class _FakeHandler:
    def __init__(self, project, app):
        self.path_args = (project, app)
        self.headers = {}
        self.body = b""

    def set_header(self, name, value):
        self.headers[name] = value

    def write(self, chunk):
        self.body += chunk if isinstance(chunk, bytes) else chunk.encode()


def _static_route_entry() -> tuple:
    """The single ``_app_spec`` entry serving ``/apps/<project>/static/``."""
    entries = [e for e in _app_spec["handlers"] if "/static/" in e[0]]
    assert len(entries) == 1, f"expected one app-static route, got {entries!r}"
    return entries[0]


class FlatAppStaticTest(AsyncHTTPTestCase):
    """A flat app's ``static/`` serves and stays confined: its dir is
    ``<apps_root>/static``, so the guard holds against the apps root
    itself rather than a project subdirectory of it."""

    def setUp(self):
        """Tree built before ``super().setUp()``, which calls get_app()."""
        self._tmp = tempfile.TemporaryDirectory()
        self._apps_root = os.path.join(self._tmp.name, "examples")
        static_dir = os.path.join(self._apps_root, "static")
        os.makedirs(static_dir)

        with open(os.path.join(static_dir, "d3.v7.min.js"), "w") as f:
            f.write("// legit static asset\n")
        with open(os.path.join(self._apps_root, "chat_server.py"), "w") as f:
            f.write("SECRET = 'server-side source that must not leak'\n")

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self._tmp.cleanup()

    def get_app(self) -> Application:
        """The production route entry, with only its apps_root redirected."""
        pattern, handler, kwargs = _static_route_entry()
        return Application(
            [(pattern, handler, {**kwargs, "apps_root": self._apps_root})]
        )

    def test_flat_app_static_file_is_served(self):
        resp = self.fetch("/apps/examples/static/d3.v7.min.js")
        assert resp.code == 200, (
            f"flat app static file should serve 200, got {resp.code}"
        )
        assert b"legit static asset" in resp.body

    def test_flat_app_static_honours_the_injected_root(self):
        """The handler must resolve the project against the apps root it
        was configured with, not the process-wide `config.apps`."""
        assert config.apps != self._apps_root
        assert self.fetch("/apps/examples/static/d3.v7.min.js").code == 200

    def test_traversal_out_of_a_flat_app_static_dir_is_blocked(self):
        resp = self.fetch(
            "/apps/examples/static/../chat_server.py",
            follow_redirects=False,
        )
        assert resp.code != 200, (
            "traversal to *_server.py must be refused, got 200 "
            f"(body={resp.body!r})"
        )
        assert b"SECRET" not in resp.body
