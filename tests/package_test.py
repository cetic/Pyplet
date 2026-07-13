"""
Regression tests for `ServerApplication.package`, which bundles an app's
files (plus pyplet/htpy/markupsafe sources) into the JSON payload the
browser writes into its virtual filesystem (VFS) before importing the
app's client module.

`config.apps` is a *server-side* on-disk detail and may be a bare
relative folder, a nested path, or an absolute path (see `--apps` /
`PYPLET_APPS`). The VFS keys handed to the browser must stay a fixed,
portable "apps/<project>/<file>" shape no matter which of those shapes
`config.apps` takes — otherwise the browser ends up trying to write to
(and later import from) the *server's* absolute filesystem path inside
its own virtual filesystem, which fails with a `FileNotFoundError` at
runtime (the reported bug: `config.apps` set to an absolute path, e.g.
via `PYPLET_APPS=/abs/path`, leaked that absolute path into the VFS).
"""

import gzip
import json

import pytest

from pyplet.server import _server
from pyplet.server.config import config

_APP_SERVER_SOURCE = """
from pyplet.server._server import ServerApplication


class MyProjServer(ServerApplication):
    title = "myproj"
"""


@pytest.fixture
def restore_config_apps():
    original = config.apps
    yield
    config.apps = original


class _FakeHandler:
    def __init__(self, project, app):
        self.path_args = (project, app)
        self.headers = {}
        self.body = b""

    def set_header(self, name, value):
        self.headers[name] = value

    def write(self, chunk):
        self.body += chunk if isinstance(chunk, bytes) else chunk.encode()


def _package_file_map(project, app):
    handler = _FakeHandler(project, app)
    _server.ServerApplication().package(handler)
    json_bytes = gzip.decompress(handler.body)
    return json.loads(json_bytes.decode("utf-8"))


@pytest.mark.unit
class TestPackageVfsKeys:
    """`package()`'s VFS keys for a project's own files must always be
    "apps/<project>/<file>", independent of `config.apps`'s shape."""

    def test_bare_relative_apps_dir(
        self, tmp_path, monkeypatch, restore_config_apps
    ):
        project_dir = tmp_path / "apps" / "myproj"
        project_dir.mkdir(parents=True)
        (project_dir / "myproj_server.py").write_text(_APP_SERVER_SOURCE)

        monkeypatch.chdir(tmp_path)
        config.apps = "apps"

        file_map = _package_file_map("myproj", "myproj")

        assert "apps/myproj/myproj_server.py" in file_map
        assert not any(k.startswith("/") for k in file_map)

    def test_absolute_apps_dir(self, tmp_path, restore_config_apps):
        """Regression test for the reported bug: an absolute
        `config.apps` (e.g. `PYPLET_APPS=/home/user/my_examples`) used
        to leak that absolute path straight into the VFS keys, so the
        browser tried to `open("/home/user/my_examples/.../x.py", ...)`
        inside its own virtual filesystem and failed with
        `FileNotFoundError`."""
        apps_dir = tmp_path / "my_examples"
        project_dir = apps_dir / "myproj"
        project_dir.mkdir(parents=True)
        (project_dir / "myproj_server.py").write_text(_APP_SERVER_SOURCE)

        config.apps = str(apps_dir)

        file_map = _package_file_map("myproj", "myproj")

        assert "apps/myproj/myproj_server.py" in file_map
        assert not any(k.startswith(str(apps_dir)) for k in file_map)
        assert not any(k.startswith("/") for k in file_map)

    def test_nested_relative_apps_dir(
        self, tmp_path, monkeypatch, restore_config_apps
    ):
        apps_dir = tmp_path / "sub" / "apps"
        project_dir = apps_dir / "myproj"
        project_dir.mkdir(parents=True)
        (project_dir / "myproj_server.py").write_text(_APP_SERVER_SOURCE)

        monkeypatch.chdir(tmp_path)
        config.apps = "sub/apps"

        file_map = _package_file_map("myproj", "myproj")

        assert "apps/myproj/myproj_server.py" in file_map
        assert not any(k.startswith("sub/") for k in file_map)
