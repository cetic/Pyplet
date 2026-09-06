"""On-disk layout of the apps root (``config.apps`` / ``PYPLET_APPS``).

Pyplet addresses every app as ``/apps/<project>/<app>``, so each app needs
a *project* to belong to. Two on-disk layouts produce that pairing:

* **nested** — ``<apps_root>/<project>/<app>_server.py``. One directory
  per project inside the apps root (what ``pyplet init`` creates).
* **flat** — ``<apps_root>/<app>_server.py``. The apps root *is* the
  project and takes its name from the root directory's own basename, so
  the URLs come out identical to pointing the root one level higher.

Flat support exists because pointing ``PYPLET_APPS`` at the directory that
actually holds the ``*_server.py`` files is the obvious thing to do — it is
exactly what the ``pyplet_examples`` repo's ``examples/`` folder looks like
— and a nested-only glob silently discovered nothing there.

Both layouts are honoured at once: a root holding app files *and* project
subdirectories yields all of them. Everything downstream (routes, ACLs,
per-app ``static/``, the client-side VFS, the transpiler cache) addresses
an app by ``(project, app)``, so :func:`project_dir` is the single place
that maps a project name back to its real directory.

Discovery goes through the ``glob`` module rather than ``Path.glob`` on
purpose: ``glob`` skips dot-prefixed entries, which keeps caches such as
an app's ``.transpiled/`` tree out of the results.
"""

import glob
import logging
import os
from pathlib import Path
from typing import Optional, Union

from .config import config

logger = logging.getLogger("pyplet.server.apps")

SERVER_SUFFIX = "_server.py"
CLIENT_SUFFIX = "_client.py"


def apps_root(root: Optional[Union[str, Path]] = None) -> Path:
    """*root* as an absolute path, defaulting to ``config.apps``.

    ``config.apps`` may be a bare relative folder, a nested relative path
    or an absolute one; resolving here means callers never have to care,
    and a flat root spelled ``.`` or ``examples/`` still yields a usable
    project name from its basename.

    Every function in this module takes the same optional *root* so a
    caller configured with an explicit apps root — ``AppStaticFileHandler``
    is handed one as a route kwarg — resolves against that one instead of
    the process-wide config.
    """
    return Path(config.apps if root is None else root).resolve()


def flat_project(root: Optional[Union[str, Path]] = None) -> Optional[str]:
    """Project name for apps stored directly in the apps root.

    Returns ``None`` when the root holds no ``*_server.py``/``*_client.py``
    of its own (the nested layout), or when a subdirectory already claims
    the same name — in which case the nested project wins, since it is the
    one :func:`project_dir` can address unambiguously.
    """
    root = apps_root(root)
    # A missing root simply globs empty, so no existence check is needed.
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


def project_dir(project: str, root: Optional[Union[str, Path]] = None) -> Path:
    """Absolute directory backing *project*.

    A subdirectory of the apps root takes precedence; otherwise the root
    itself backs the flat project. The returned path need not exist —
    callers that serve from it (per-app ``static/``) already treat a
    missing directory as a 404.
    """
    root = apps_root(root)
    nested = root / project
    if nested.is_dir():
        return nested
    if project == flat_project(root):
        return root
    return nested


def _discover(
    suffix: str, root: Optional[Union[str, Path]] = None
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
    root: Optional[Union[str, Path]] = None,
) -> list[tuple[str, str, Path]]:
    """``(project, app, path)`` for every discoverable ``*_server.py``."""
    return _discover(SERVER_SUFFIX, root)


def client_apps(
    root: Optional[Union[str, Path]] = None,
) -> list[tuple[str, str]]:
    """``(project, app)`` for every discoverable ``*_client.py``.

    This is what the index page and the ACL filter enumerate: an app is
    listed when it has client code to ship to the browser.
    """
    return [
        (project, app) for project, app, _ in _discover(CLIENT_SUFFIX, root)
    ]
