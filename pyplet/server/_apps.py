"""Apps-root layouts: nested ``<root>/<project>/<app>_server.py`` and flat
``<root>/<app>_server.py`` (the root is the project, named by its basename).
Pinned by ``tests/apps_layout_test.py``."""

import glob
import logging
import os
from pathlib import Path

from .config import config

logger = logging.getLogger("pyplet.server.apps")

SERVER_SUFFIX = "_server.py"
CLIENT_SUFFIX = "_client.py"


def apps_root(root: str | Path | None = None) -> Path:
    """*root*, defaulting to ``config.apps``, as an absolute path."""
    return Path(config.apps if root is None else root).resolve()


def flat_project(root: str | Path | None = None) -> str | None:
    """Project name for apps sitting in the apps root itself, else
    ``None`` (nested layout, or a subdirectory already claims the name).
    """
    root = apps_root(root)
    has_app_files = any(
        glob.glob(f"*{suffix}", root_dir=root)
        for suffix in (SERVER_SUFFIX, CLIENT_SUFFIX)
    )
    if not has_app_files:
        return None

    name = root.name
    if (root / name).is_dir():
        logger.warning(
            "Apps root %s holds app files directly, but a subdirectory "
            "named %r already claims that project name — the apps in the "
            "root itself are ignored. Rename one of the two.",
            root,
            name,
        )
        return None

    if not name.isidentifier():
        logger.warning(
            "Apps root %s holds app files directly, but %r is not a valid "
            "project name (letters, digits and underscores only, not "
            "starting with a digit), so /apps/%s/... cannot be routed. "
            "Rename the directory or move the apps into a subdirectory.",
            root,
            name,
            name,
        )

    return name


def project_dir(project: str, root: str | Path | None = None) -> Path:
    """Absolute directory backing *project*: a subdirectory of the apps
    root, else the root itself for the flat project. Need not exist.
    """
    root = apps_root(root)
    nested = root / project
    if nested.is_dir():
        return nested
    if project == flat_project(root):
        return root
    return nested


def _discover(
    suffix: str, root: str | Path | None = None
) -> list[tuple[str, str, Path]]:
    """``(project, app, path)`` for every ``*<suffix>`` under the root."""
    root = apps_root(root)
    found: list[tuple[str, str, Path]] = []

    flat = flat_project(root)
    if flat is not None:
        for name in sorted(glob.glob(f"*{suffix}", root_dir=root)):
            found.append((flat, name[: -len(suffix)], root / name))

    for name in sorted(glob.glob(f"*/*{suffix}", root_dir=root)):
        project, filename = name.replace(os.sep, "/").split("/")
        found.append((project, filename[: -len(suffix)], root / name))

    return found


def server_modules(
    root: str | Path | None = None,
) -> list[tuple[str, str, Path]]:
    """``(project, app, path)`` for every discoverable ``*_server.py``."""
    return _discover(SERVER_SUFFIX, root)


def client_apps(
    root: str | Path | None = None,
) -> list[tuple[str, str]]:
    """``(project, app)`` for every discoverable ``*_client.py``."""
    return [
        (project, app) for project, app, _ in _discover(CLIENT_SUFFIX, root)
    ]
