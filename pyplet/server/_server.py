import asyncio
import base64
import glob
import gzip
import importlib.util
import json
import logging
import os
import re
import secrets
import sys
import textwrap
import types
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple

import markupsafe
import tornado
import tornado.web
import tornado.websocket

import pyplet
from pyplet.server._transpiler import transpile_to_pyscript
from pyplet.server.config import config

from ..shared.dom import div, link, script
from . import magiclink, oauth, templates

# Configure logging
logger = logging.getLogger("pyplet.server")


server_applications: Dict[Tuple[str, str], "ServerApplication"] = {}

# Synthetic module-name prefix used when loading `*_server.py` app modules.
# App discovery loads modules directly from their file path (see
# `_load_server_module`) rather than importing them via a dotted name
# derived from `config.apps`, so registration keeps working regardless of
# whether `config.apps` is a bare relative folder, a nested path, or an
# absolute path.
_APPS_MODULE_PREFIX = "_pyplet_apps"

# Fixed virtual directory name for app files inside the browser-side
# (Pyodide/MicroPython) virtual filesystem — see `ServerApplication.package`
# and `ServerApplication.serve`. Kept separate from `config.apps` (the
# *server's* on-disk apps directory, which may be relative, nested, or
# absolute) so the client-side VFS layout and import path stay portable
# regardless of how `config.apps` is configured.
_APPS_VFS_ROOT = "apps"

# ---------------------------------------------------------------------------
# Auth gate mixin
# ---------------------------------------------------------------------------


class _AuthMixin:
    """
    Tornado handler mixin that enforces platform-level authentication.

    When auth is disabled (no OAuth provider configured) every request
    passes through unchanged.  When auth is enabled:

    * Unauthenticated requests to HTML pages → redirect to /login.
    * Unauthenticated requests to other resources (zip, ws) → 401.
    * Authenticated but unauthorised → 403.
    """

    # Sub-classes set this to True for WebSocket handlers where redirects
    # are not meaningful.
    _is_ws: bool = False

    def get_current_user(self):
        if not oauth.auth_enabled():
            # Return a sentinel so Tornado's @authenticated decorator works.
            return {"email": "", "name": "anonymous", "provider": None}
        return oauth.get_session(self)

    def _require_auth(
        self, project: str | None = None, app: str | None = None
    ):
        """
        Enforce auth + ACL.  Returns the user dict on success, or None if
        the request has already been terminated (redirect / error written).
        """
        if not oauth.auth_enabled():
            return {"email": "", "name": "anonymous", "provider": None}

        user = oauth.get_session(self)
        if user is None:
            if self._is_ws:
                self.set_status(401)
                self.write("Unauthenticated")
                self.finish()
            else:
                next_url = self.request.uri
                self.redirect(f"/login?next={next_url}")
            return None

        if project is not None and app is not None:
            if not oauth.is_app_permitted(project, app, user["email"]):
                self.set_status(403)
                self.finish(
                    f"<html><body><h3>403 Forbidden</h3>"
                    f"<p>Your account ({user['email']}) is not permitted "
                    f"to access {project}/{app}.</p>"
                    f'<p><a href="/">Back to home</a></p>'
                    f"</body></html>"
                )
                return None

        return user


# ---------------------------------------------------------------------------
# Static file handler (no auth required)
# ---------------------------------------------------------------------------


class StaticFileHandler(tornado.web.StaticFileHandler):
    """
    A static file handler that sets the Cache-Control header to no-cache.
    """

    def set_extra_headers(self, path: str) -> None:
        """Sets the Cache-Control header to no-cache.

        Args:
            path (str): The path of the requested resource.
        """
        self.set_header("Cache-Control", "no-cache")


# ---------------------------------------------------------------------------
# Application handlers
# ---------------------------------------------------------------------------
def load_favicon_as_data_uri(filepath):
    """Reads the SVG file and converts it to a Base64 Data URI."""
    if not os.path.exists(filepath):
        logger.warning(f"Favicon not found at {filepath}")
        return None

    with open(filepath, "rb") as f:
        svg_data = f.read()

    # Encode the binary SVG data to a base64 string
    b64_encoded = base64.b64encode(svg_data).decode("utf-8")

    # Format it as a Data URI for SVG
    return f"data:image/svg+xml;base64,{b64_encoded}"


# Matches the opening <head ...> tag so the favicon can be inserted
# right after it.
_HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
# Matches any <link ...> tag so its `rel` attribute can be inspected.
_LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
# Matches a `rel` attribute, quoted or unquoted, inside a tag.
_REL_ATTR_RE = re.compile(
    r"""rel\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+))""", re.IGNORECASE
)


def _has_favicon_link(html_str: str) -> bool:
    """Whether `html_str` already declares a favicon `<link>` tag."""
    for link_tag in _LINK_TAG_RE.findall(html_str):
        match = _REL_ATTR_RE.search(link_tag)
        if not match:
            continue
        rel_value = next(g for g in match.groups() if g is not None)
        if "icon" in rel_value.lower():
            return True
    return False


class BaseHandler(tornado.web.RequestHandler):
    """
    A base handler that provides a custom method to inject
    an inline Base64 SVG favicon into raw HTML strings.
    """

    def write_html(self, html_content):
        # 1. Check if we actually have a favicon loaded in settings
        favicon_uri = self.application.settings.get("favicon_data_uri")
        if not favicon_uri:
            self.write(html_content)
            return

        # 2. Normalize content to a plain `str`. Going through bytes
        # matters here: htpy nodes/markupsafe.Markup render via `str()`
        # into a `Markup` instance, and slicing/concatenating a plain str
        # onto a `Markup` auto-*escapes* that plain str (e.g. our raw
        # <link> tag below would come out as "&lt;link ...&gt;"). Encoding
        # then decoding strips the Markup type, leaving a genuine str.
        if isinstance(html_content, bytes):
            html_bytes = html_content
        else:
            html_bytes = str(html_content).encode("utf-8")
        html_str = html_bytes.decode("utf-8")

        # 3. Inject the favicon right after <head>, unless one is
        # already present anywhere in the document.
        head_match = _HEAD_OPEN_RE.search(html_str)
        if head_match and not _has_favicon_link(html_str):
            favicon_tag = (
                f'<link rel="icon" type="image/svg+xml" href="{favicon_uri}">'
            )
            insert_at = head_match.end()
            html_str = (
                html_str[:insert_at] + favicon_tag + html_str[insert_at:]
            )

        self.write(html_str.encode("utf-8"))


class AboutHandler(_AuthMixin, BaseHandler):
    """
    GET  /about  — show the about page.
    """

    async def get(self):
        user = self._require_auth()
        if user is None:
            return
        self.write_html(
            str(
                markupsafe.Markup(  # nosec
                    templates.about_template(self, user)
                )
            ).encode("UTF-8")
        )


class PackageHandler(_AuthMixin, BaseHandler):
    """A handler for serving package resources."""

    async def get(self, project_name: str, app_name: str) -> None:
        """Serves the package resource for the given project and app.

        Args:
            project_name (str): The name of the project.
            app_name (str): The name of the app.
        """
        user = self._require_auth(project_name, app_name)

        if user is None:
            return

        application = server_applications[project_name, app_name]
        application.package(self)


class LoginHandler(_AuthMixin, BaseHandler):
    """
    GET  /login  — show login page (provider buttons) or redirect to / if
                   already authenticated.
    """

    async def get(self):
        if oauth.auth_enabled() and oauth.get_session(self) is not None:
            self.redirect("/")
            return
        self.write_html(str(templates.login_template(self)).encode("UTF-8"))


class IndexHandler(_AuthMixin, BaseHandler):
    """
    GET  /  — show the index page with the apps the user is allowed to see.
    """

    async def get(self):
        user = self._require_auth()
        if user is None:
            return
        self.write_html(
            str(templates.index_template(self, user)).encode("UTF-8")
        )


class LogoutHandler(tornado.web.RequestHandler):
    async def get(self):
        oauth.clear_session(self)
        self.redirect("/")


class HealthzHandler(tornado.web.RequestHandler):
    """
    GET  /healthz  — unauthenticated process-liveness probe.

    Deliberately a plain handler (NOT ``_AuthMixin``): a liveness probe must
    answer for an LB / systemd / k8s without a session, even when auth is
    enabled.  Process-up only — it performs NO database / provider / event-loop
    checks (deep readiness is the app's ``/readyz`` route).  Lives in core's
    static ``_app_spec`` so it answers for every pyplet app, even when an app
    module failed to import (``astart`` swallows app-import errors).
    """

    async def get(self):
        self.set_header("Content-Type", "application/json")
        self.write({"status": "ok"})


class OAuthLoginHandler(tornado.web.RequestHandler):
    """
    GET  /oauth/login?provider=<name>  — kick off the OAuth flow.
    """

    async def get(self):
        provider = self.get_argument("provider", None)
        if provider not in oauth.enabled_providers():
            self.set_status(400)
            self.write(f"Unknown or unconfigured provider: {provider!r}")
            return
        await oauth.start_login(self, provider)


class OAuthCallbackHandler(tornado.web.RequestHandler):
    """
    GET  /oauth/callback  — OAuth provider redirects here with ?code=…&state=…
    """

    async def get(self):
        await oauth.handle_callback(self)


class MagicLinkRequestHandler(tornado.web.RequestHandler):
    """
    POST /auth/email  — accepts an e-mail address, sends a magic link.
    """

    async def post(self):
        await magiclink.handle_request(self)


class MagicLinkVerifyHandler(tornado.web.RequestHandler):
    """
    GET  /auth/verify?token=<token>  —
    validates the token and logs the user in.
    """

    async def get(self):
        await magiclink.handle_verify(self)


class AppHandler(_AuthMixin, BaseHandler):
    async def get(self, project_name, app_name):
        user = self._require_auth(project_name, app_name)
        if user is None:
            return
        application = server_applications[project_name, app_name]
        application.serve(self)


class ServerWebSocket(_AuthMixin, tornado.websocket.WebSocketHandler):
    closing_message = pyplet.WebSocket.closing_message
    _is_ws = True

    def check_origin(self, origin: str) -> bool:
        """Allow same-origin WS upgrades OR the deployed ``PYPLET_URL`` origin.

        Story 18.18 (SECURI-4). Tornado's default ``check_origin`` accepts only
        a request whose ``Origin`` host equals the ``Host`` header — which the
        edge can break by rewriting ``Host``. We additionally allow an origin
        whose host matches the configured deployed origin (``config.url`` /
        ``PYPLET_URL``), compared host-only so the edge's scheme/port do not
        matter. When ``PYPLET_URL`` is unset (local dev) we fall back to
        Tornado's default same-origin result, so ``localhost`` still connects.

        Caveat (documented): Tornado invokes ``check_origin`` ONLY when an
        ``Origin`` header is present, so an Origin-less (non-browser) upgrade
        is not blocked here — the real gate against anonymous access remains
        ``_AuthMixin._require_auth`` in ``open``.

        Args:
            origin: The request's ``Origin`` header value.

        Returns:
            ``True`` to accept the cross-origin upgrade, ``False`` to reject
            (Tornado answers the handshake with 403).
        """
        if super().check_origin(origin):
            return True
        allowed = config.url
        if not allowed:
            return False
        return (
            urllib.parse.urlparse(origin).hostname
            == urllib.parse.urlparse(allowed).hostname
        )

    def get_compression_options(self):
        """Enable WebSocket ``permessage-deflate`` compression.

        Returning a (possibly empty) dict opts the connection into Tornado's
        per-message deflate extension; the client offers the extension and this
        handler accepts it during the handshake. ``compression_level`` 6 is
        zlib's default speed/ratio trade-off — a good fit for the app's
        chatty JSON/text frames without excessive CPU per message.

        Returns:
            A dict of compression options enabling ``permessage-deflate``.
        """
        return {"compression_level": 6}

    async def open(self, project_name, app_name):
        user = self._require_auth(project_name, app_name)
        if user is None:
            self.close(1008, "Unauthorized")
            return
        self.login = user["email"]

        application = server_applications[project_name, app_name]
        self.queue = asyncio.Queue()
        asyncio.create_task(application.websocket_server_loop(self))

    async def on_message(self, message):
        await self.queue.put(message)

    async def receive(self):
        return await self.queue.get()

    async def send(self, message):
        await super().write_message(
            message, binary=not isinstance(message, str)
        )

    def on_close(self):
        asyncio.get_running_loop().create_task(self.aclose())

    async def aclose(self):
        await self.queue.put(self.closing_message)


# ---------------------------------------------------------------------------
# Tornado application spec
# ---------------------------------------------------------------------------

_app_spec = {
    "handlers": [
        (
            r"/pyodide/(.*)",
            tornado.web.StaticFileHandler,
            {"path": os.path.join(config.apps, "../pyodide")},
        ),
        (r"/healthz", HealthzHandler),
        (r"/", IndexHandler),
        (r"/about", AboutHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/oauth/login", OAuthLoginHandler),
        (r"/oauth/callback", OAuthCallbackHandler),
        (r"/auth/email", MagicLinkRequestHandler),
        (r"/auth/verify", MagicLinkVerifyHandler),
        # App static resources (static files)
        (
            # ONE capture group covering the app name,
            # the static folder, and the filename
            r"/apps/([a-zA-Z_][a-zA-Z0-9_]*/static/.*)",
            tornado.web.StaticFileHandler,
            {"path": config.apps},
        ),
        # App upload endpoint (for upload() and upload_area())
        (
            r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/upload/.*",
            tornado.web.RequestHandler,
        ),
        (
            r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*)\.json",
            PackageHandler,
        ),
        (
            r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*)\.ws",
            ServerWebSocket,
        ),
        (
            r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*)",
            AppHandler,
        ),
        (
            r"/.*",
            tornado.web.RedirectHandler,
            {"url": "/", "permanent": False},
        ),
    ],
    "debug": config.debug == "1",
    # Signs session cookies.  Falls back to a per-process random value so the
    # server still works without PYPLET_COOKIE_SECRET
    # (sessions lost on restart).
    "cookie_secret": config.oauth_cookie_secret or secrets.token_hex(32),
    # Max WebSocket frame size. Tornado defaults to ~10 MB, which a base64'd
    # document upload exceeds (killing the socket before app code runs). The
    # default 40 MB carries a 25 MB upload (~33 MB frame) with headroom; raise
    # PYPLET_WS_MAX_MESSAGE_MB in lockstep with any app's per-document cap.
    "websocket_max_message_size": config.ws_max_message_mb * 1024 * 1024,
}


def _ensure_namespace_package(name: str, search_path: Optional[list] = None):
    """Get-or-create a namespace package registered in `sys.modules`.

    `search_path`, when given, becomes the package's `__path__`, which
    lets Python's own import machinery locate real submodules under that
    directory on demand — this is what makes ordinary intra-project
    imports (e.g. `from . import other_server`) work for modules loaded
    by `_load_server_module`.
    """
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = search_path if search_path is not None else []
        module.__package__ = name
        sys.modules[name] = module
    elif search_path is not None:
        module.__path__ = search_path
    return module


def _load_server_module(path: str) -> str:
    """Import a `<project>/<app>_server.py` module under a synthetic,
    stable package hierarchy (`_pyplet_apps.<project>.<app>_server`) and
    return the module name it was loaded under.

    A real (if synthetic) package hierarchy is registered in
    `sys.modules` — rather than loading the file in isolation via
    `spec_from_file_location` — so Python's own import machinery handles
    the module. That is what makes ordinary intra-project imports (e.g.
    `from . import other_server`) keep working: the project package's
    `__path__` points at its real on-disk directory, so Python can find
    sibling `*_server.py` modules there when such an import is resolved.

    This stays independent of `config.apps`'s literal shape (bare
    relative folder, nested path, or absolute path) since the synthetic
    prefix is never derived from it.
    """
    file_path = Path(path)
    project_dir = file_path.parent.resolve()
    project_name = file_path.parent.name

    _ensure_namespace_package(_APPS_MODULE_PREFIX)
    _ensure_namespace_package(
        f"{_APPS_MODULE_PREFIX}.{project_name}",
        # Must be an absolute path: Python's import machinery caches a
        # per-directory finder in `sys.path_importer_cache` keyed by the
        # literal path string, so a relative string reused under a
        # different cwd (e.g. across server restarts, or two projects
        # that both happen to be named "apps/<project>") would return a
        # stale finder pointing at the wrong (or now-gone) directory.
        search_path=[str(project_dir)],
    )

    module_name = f"{_APPS_MODULE_PREFIX}.{project_name}.{file_path.stem}"
    module = importlib.import_module(module_name)
    return module.__name__


# ---------------------------------------------------------------------------
# Fail-closed startup policy — production debug guard (Story 18.18, DEPLOY-8)
# ---------------------------------------------------------------------------


class DebugConfigError(RuntimeError):
    """Raised at startup when the production profile runs with debug on.

    Refusing to boot is intentional: Tornado debug mode enables autoreload and
    full traceback pages, which must never be exposed on the production profile
    (``PYPLET_REQUIRE_AUTH=1``). Mirrors ``oauth.AuthConfigError``.
    """


def enforce_startup_debug_policy() -> None:
    """Refuse to boot the production profile with Tornado debug mode on
    (DEPLOY-8, Story 18.18).

    On the production profile (``PYPLET_REQUIRE_AUTH=1``) raises
    ``DebugConfigError`` when ``PYPLET_DEBUG=1`` (the ``config.py`` default),
    because debug mode enables autoreload and exposes traceback pages — leaking
    source/stack and re-exec'ing on file change. Off the production profile
    (``PYPLET_REQUIRE_AUTH`` unset/``0``) it is a no-op, so debug + autoreload
    stay available for the everyday local dev loop.

    The gate is ``config.require_auth`` — NOT ``oauth.auth_enabled()`` —
    deliberately mirroring ``oauth.enforce_startup_auth_policy``'s own
    production gate. Gating on ``auth_enabled()`` would brick the authenticated
    dev loop (a provider client-id set + debug + autoreload), which is a
    daily-driver, not production.

    Side effects: reads ``config``.
    Raises: ``DebugConfigError`` to abort boot on a production-profile breach.
    """
    if config.require_auth == "1" and config.debug == "1":
        raise DebugConfigError(
            "PYPLET_REQUIRE_AUTH=1 (production profile) but PYPLET_DEBUG=1 — "
            "refusing to boot. Tornado debug mode enables autoreload and "
            "exposes traceback pages. Set PYPLET_DEBUG=0 in production, or "
            "unset PYPLET_REQUIRE_AUTH for an explicitly open local-dev run."
        )


def _merge_app_declared_routes() -> list[tuple]:
    """Splice app-declared ``routes()`` into ``_app_spec["handlers"]``.

    Every registered application is asked for its ``routes()`` and the
    result is inserted BEFORE the catch-all ``r"/.*"`` redirect, which is
    the LAST entry of ``_app_spec["handlers"]`` (see the module-level
    definition) — a route listed after it would be shadowed into a
    redirect and never reached. Insertion is a ``[-1:-1]`` slice
    assignment, so the catch-all stays last.

    Called from ``astart()`` once the app modules are loaded (that is what
    populates ``server_applications``) and before the Tornado
    ``Application`` is built from ``_app_spec`` — a merge after the
    Application exists would have no effect on the running server.

    A failing ``routes()`` is logged and skipped so one broken app cannot
    take the others down.

    Returns:
        The handler tuples that were spliced in (empty list if none).
    """
    app_declared_handlers: list[tuple] = []
    for instance in server_applications.values():
        try:
            app_declared_handlers.extend(instance.routes())
        except Exception as e:
            logger.error(
                "Failed to read routes() from %s: %s",
                type(instance).__name__,
                e,
                exc_info=True,
            )
    if app_declared_handlers:
        _app_spec["handlers"][-1:-1] = app_declared_handlers
        logger.info(
            "Registered %d app-declared route(s) before catch-all redirect",
            len(app_declared_handlers),
        )
    return app_declared_handlers


async def astart():
    # Load all server applications FIRST: importing each *_server.py
    # fires ServerApplication.__init_subclass__, which registers the
    # instance in server_applications. Anything derived from that
    # registry has to run once it is populated, so the modules are
    # loaded before the Tornado Application is built from _app_spec.
    server_modules = glob.glob(f"{config.apps}/*/*_server.py")
    for path in server_modules:
        try:
            module_name = _load_server_module(path)
            logger.debug(f"Loaded module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load module {path}: {e}", exc_info=True)

    # Fail-closed auth policy (Story 17.6, PB-1): on the production profile,
    # refuse to boot on a misdelivered auth config rather than serve
    # anonymously. Runs once the modules are loaded, so the policy sees
    # every discovered application.
    oauth.enforce_startup_auth_policy(magiclink_enabled=magiclink.enabled())

    # Story 18.18 (DEPLOY-8): on the production profile, refuse to boot with
    # Tornado debug on (autoreload + traceback pages must never ship to prod).
    enforce_startup_debug_policy()

    # Merge the routes each app declares into the handler table before the
    # Tornado Application is built from _app_spec.
    _merge_app_declared_routes()

    favicon_uri = None
    if config.favicon:
        # Relative paths (e.g. the default "../images/...") are resolved
        # against the pyplet package directory, not the process CWD, so
        # the bundled favicon is found regardless of where the server
        # is launched from.
        favicon_path = Path(config.favicon)
        if not favicon_path.is_absolute():
            favicon_path = Path(pyplet.__file__).parent / favicon_path
        favicon_path = favicon_path.resolve()

        favicon_uri = load_favicon_as_data_uri(str(favicon_path))
        logger.info(
            "Using favicon: %s (Data URI length: %s)",
            favicon_path,
            len(favicon_uri) if favicon_uri else "N/A",
        )

    # Inject it into the Tornado settings so the Handlers can find it
    _app_spec["favicon_data_uri"] = favicon_uri

    app = tornado.web.Application(**_app_spec)
    # Story 18.18 (DEPLOY-8): trust the edge's X-Forwarded-For / -Proto so the
    # app sees the real client IP + https scheme behind the reverse proxy. No
    # proxy in local dev ⇒ those headers are absent ⇒ behavior unchanged.
    app.listen(config.port, config.address, xheaders=True)

    url = config.url or f"http://{config.address}:{config.port}"
    logger.info(f"Pyplet server started on {url}")
    logger.info(f"Loaded {len(server_applications)} application(s)")

    methods = oauth.enabled_providers()

    if magiclink.enabled():
        methods.append("magic-link")
    if methods:
        logger.info("Authentication enabled via: %s", ", ".join(methods))
    else:
        logger.info("Authentication disabled (no provider configured)")

    await asyncio.Event().wait()


# ---------------------------------------------------------------------------
# Base class for user applications
# ---------------------------------------------------------------------------


class ServerApplication:
    title: Optional[str] = None
    client_libraries: Tuple[str] = ()
    mcp_tools = ()
    interpreter: str = "py"

    def websocket_server_loop(
        self, websocket: tornado.websocket.WebSocketHandler
    ): ...

    def package(self, handler):
        project, app = handler.path_args
        pyplet_root = str(Path(pyplet.__file__).parent.parent)

        # Safely locate htpy and get its parent directory
        htpy_location = str(
            importlib.util.find_spec("htpy").submodule_search_locations[0]
        )
        htpy_parent = str(Path(htpy_location).parent)
        markupsafe_location = str(
            importlib.util.find_spec("markupsafe").submodule_search_locations[
                0
            ]
        )
        markupsafe_parent = str(Path(markupsafe_location).parent)

        file_map = {}
        files = [
            (pyplet_root, "pyplet/*", ""),
            (pyplet_root, "pyplet/shared/**", ""),
            (pyplet_root, "pyplet/client/**", ""),
            # root_dir is resolved to an absolute path and the pattern
            # kept relative to it, so the resulting VFS keys are always
            # "apps/<project>/..." — never leaking `config.apps`'s own
            # (possibly absolute, nested, etc.) on-disk shape into the
            # browser-side virtual filesystem.
            (
                str(Path(config.apps).resolve()),
                f"{project}/**",
                _APPS_VFS_ROOT,
            ),
            # Inject htpy dynamically!
            (htpy_parent, "htpy/**", ""),
            (markupsafe_parent, "markupsafe/**", ""),
        ]

        # Define the exact, absolute path to the project's static folder
        project_static_dir = Path(config.apps, project, "static").resolve()

        for root_dir, pattern, prefix in files:
            for file in glob.glob(pattern, root_dir=root_dir, recursive=True):
                # Skip __pycache__ and similar hidden files
                if file.startswith("."):
                    continue

                full_path = Path(root_dir, file)
                if not full_path.is_file():
                    continue

                # Filter out cache and compiled bytecode
                if (
                    "__pycache__" in full_path.__str__()
                    or full_path.suffix == ".pyc"
                ):
                    continue

                # Filter out project static folder
                if full_path.resolve().is_relative_to(project_static_dir):
                    continue

                target_path = Path(prefix, file)

                # Read as bytes and encode to base64 for JSON safety
                # 1. Open strictly in binary mode to prevent
                # UnicodeDecodeError on assets
                with full_path.open("rb") as source_file:
                    raw_bytes = source_file.read()

                # 2. Process Python files through the transpiler
                if full_path.suffix == ".py":
                    try:
                        # Decode to string for AST manipulation
                        code_str = raw_bytes.decode("utf-8")

                        # Transpile ONCE to save CPU time
                        transpiled_str = transpile_to_pyscript(
                            code_str,
                            full_path.name,
                            targer_interpreter=self.interpreter,
                        )
                        content_bytes = transpiled_str.encode("utf-8")

                        # Write the transpiled content to
                        # "apps"/.transpiled/...
                        app_root = Path(config.apps) / project
                        transpiled_path = (
                            app_root / ".transpiled" / target_path
                        )
                        transpiled_path.parent.mkdir(
                            parents=True, exist_ok=True
                        )

                        with transpiled_path.open(
                            "w", encoding="utf-8"
                        ) as transpiled_file:
                            transpiled_file.write(transpiled_str)

                    except UnicodeDecodeError:
                        # Fallback if a .py file is somehow weirdly
                        # encoded/binary
                        logger.warning(
                            f"{full_path} is not valid UTF-8. "
                            "Skipping transpilation."
                        )
                        content_bytes = raw_bytes

                # 3. Handle all other files (images, data, etc.) natively
                else:
                    content_bytes = raw_bytes

                # 4. Encode the final bytes to base64 for the JSON payload
                encoded_content = base64.b64encode(content_bytes).decode(
                    "utf-8"
                )
                file_map[target_path.as_posix()] = encoded_content

        # Convert to JSON and compress
        json_bytes = json.dumps(file_map).encode("utf-8")
        compressed_bytes = gzip.compress(json_bytes)

        # Set headers so the browser natively decompresses the payload
        handler.set_header("Content-Type", "application/json")
        handler.set_header("Content-Encoding", "gzip")
        handler.write(compressed_bytes)

    def serve(self, handler):
        project, app = handler.path_args

        # Update the extension to .json
        # COULD BE THE EXAMPLE RELATED BUG
        app_package = f"/apps/{project}/{app}.json"

        # Inject PyScript core scripts
        head_content = [
            link(
                rel="stylesheet",
                href="https://pyscript.net/releases/2026.7.2/core.css",
            ),
            script(
                type="module",
                src="https://pyscript.net/releases/2026.7.2/core.js",
            ),
            link(
                rel="stylesheet",
                href="https://code.jquery.com/ui/1.14.2/themes/base/jquery-ui.css",  # noqa: E501
            ),
            script(src="https://code.jquery.com/jquery-4.0.0.min.js"),
            script(src="https://code.jquery.com/ui/1.14.2/jquery-ui.min.js"),
        ]

        # The Python script to run on the client
        # (works in both Pyodide and MicroPython)
        python_code = textwrap.dedent(f"""
import base64
import js
import json
import os
import sys

from js import fetch

# Polyfill os.makedirs
def ensure_dir(path):
    if not path: return
    parts = path.split("/")
    current_path = ""
    for part in parts:
        if not part: continue

        # Only add the slash if current_path is not empty
        if current_path:
            current_path += "/"
        current_path += part

        try:
            os.mkdir(current_path)
        except OSError:
            pass

# Top-level await for the package
response = await fetch('{app_package}')

if not response.ok:
    print(
        "Failed to fetch package: HTTP "
        + f"{{response.status}}"
    )
else:
    raw_text = await response.text()
    file_data = json.loads(raw_text)

    # Write files to the VFS
    for filepath, b64_content in file_data.items():
        dir_name = os.path.dirname(filepath)
        if dir_name:
            ensure_dir(dir_name)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(b64_content))

    # --- Mock the typing module for MicroPython ---
    if sys.implementation.name == "micropython":
        # 1. Mock Typing
        if "typing" not in sys.modules:
            class MockTyping:
                TYPE_CHECKING = False
                def __getattr__(self, name): return self
                def __getitem__(self, key): return self
                def __or__(self, other): return self
                def __ror__(self, other): return self

                def __call__(self, *args, **kwargs):
                    # If they are doing t.cast(Type, value),
                    # it's safer to return the value.
                    # Otherwise, just return self.
                    if (
                        args and hasattr(args[0], "__class__")
                        and len(args) == 2
                    ):
                        return args[1]
                    return self
            sys.modules["typing"] = MockTyping()

        # 2. Mock __future__
        if "__future__" not in sys.modules:
            class MockFuture:
                def __getattr__(self, name): return self
            sys.modules["__future__"] = MockFuture()

        # 3. Polyfill importlib
        if "importlib" not in sys.modules:
            class MockImportlib:
                @staticmethod
                def import_module(name, package=None):
                    if name.startswith('.'):
                        if not package:
                            raise TypeError(
                                "Relative imports require"
                                + " the 'package' argument"
                            )
                        name = package + name

                    return __import__(
                        name, globals(), locals(), ['']
                    )

            sys.modules["importlib"] = MockImportlib()
        # 4. Mock collections.abc
        if "collections.abc" not in sys.modules:
            class DummyGenericMeta(type):
                def __getitem__(cls, key):
                    return cls
                def __or__(cls, other):
                    return cls
                def __ror__(cls, other):
                    return cls

            class MockCollectionsAbc:
                TYPE_CHECKING = False
                def __getattr__(self, name):
                    cls = DummyGenericMeta(name, (), {{}})
                    # Cache so repeated access returns the same object
                    try:
                        object.__setattr__(self, name, cls)
                    except (AttributeError, TypeError):
                        pass
                    return cls

            mock_abc = MockCollectionsAbc()
            sys.modules["collections.abc"] = mock_abc

            # --- NEW: Attach it to the base collections module ---
            import collections
            try:
                # Try to attach it directly
                collections.abc = mock_abc
            except AttributeError:
                # If MicroPython's built-in collections is read-only, wrap it!
                class CollectionsWrapper:
                    abc = mock_abc
                    def __getattr__(self, name):
                        return getattr(collections, name)
                sys.modules["collections"] = CollectionsWrapper()

        # 5. Mock typing_extensions (highly recommended for modern libs)
        def dummy_decorator(*args, **kwargs):
            # If used with arguments: @deprecated("msg")
            def wrapper(func): return func
            # If used without arguments: @deprecated
            if len(args) == 1 and callable(args[0]): return args[0]
            return wrapper

        if "typing_extensions" not in sys.modules:
            class MockTypingExtensions:
                deprecated = staticmethod(dummy_decorator)
                def __getattr__(self, name):
                    # Fallback to the typing mock for anything else
                    return sys.modules["typing"]
            sys.modules["typing_extensions"] = MockTypingExtensions()
        # 6. Mock string.Formatter for markupsafe
        import string
        if not hasattr(string, "Formatter"):
            # Provide a basic implementation so
            # EscapeFormatter can inherit from it
            class MockFormatter:
                def format(self, format_string, *args, **kwargs):
                    return format_string.format(*args, **kwargs)

                def format_field(self, value, format_spec):
                    # Fallback to standard python format()
                    return format(value, format_spec)

            try:
                # Try to attach it directly
                string.Formatter = MockFormatter
            except AttributeError:
                # Wrap it if string is a read-only C module
                class StringWrapper:
                    Formatter = MockFormatter
                    def __getattr__(self, name):
                        return getattr(string, name)

                sys.modules["string"] = StringWrapper()
        # 7. Mock weakref.WeakSet
        import weakref
        if not hasattr(weakref, "WeakSet"):
            # Provide a dummy WeakSet that behaves exactly like a standard set
            class MockWeakSet:
                def __init__(self, elements=()):
                    self.data = set(elements)
                def add(self, item): self.data.add(item)
                def remove(self, item): self.data.remove(item)
                def discard(self, item): self.data.discard(item)
                def pop(self): return self.data.pop()
                def clear(self): self.data.clear()
                def update(self, other): self.data.update(other)
                def __contains__(self, item): return item in self.data
                def __iter__(self): return iter(self.data)
                def __len__(self): return len(self.data)

            try:
                # Try to attach it directly
                weakref.WeakSet = MockWeakSet
            except AttributeError:
                # Wrap it if weakref is a read-only C module
                class WeakrefWrapper:
                    WeakSet = MockWeakSet
                    def __getattr__(self, name):
                        return getattr(weakref, name)

                sys.modules["weakref"] = WeakrefWrapper()
        # 8. Mock warnings.deprecated
        try:
            import warnings
            if not hasattr(warnings, "deprecated"):
                try:
                    warnings.deprecated = dummy_decorator
                except AttributeError:
                    class WarningsWrapper:
                        deprecated = dummy_decorator
                        def __getattr__(self, name):
                            return getattr(warnings, name)
                    sys.modules["warnings"] = WarningsWrapper()
        except ImportError:
            pass
            # If warnings doesn't exist at all,
            # htpy falls back to typing_extensions
        # 9. Mock the keyword module
        if "keyword" not in sys.modules:
            class MockKeyword:
                kwlist = [
                    'False', 'None', 'True', 'and', 'as', 'assert', 'async',
                    'await', 'break', 'class', 'continue', 'def', 'del',
                    'elif', 'else', 'except', 'finally', 'for', 'from',
                    'global', 'if', 'import', 'in', 'is', 'lambda',
                    'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
                    'try', 'while', 'with', 'yield'
                ]

                @staticmethod
                def iskeyword(s):
                    return s in sys.modules["keyword"].kwlist

            sys.modules["keyword"] = MockKeyword()
        # 10. Mock functools.lru_cache (and .cache just in case!)
        try:
            import functools
        except ImportError:
            # Some extremely minimal MicroPython builds drop functools entirely
            class MockFunctools: pass
            functools = MockFunctools()
            sys.modules["functools"] = functools

        if not hasattr(functools, "lru_cache"):
            def mock_lru_cache(*args, **kwargs):
                # If used with arguments: @lru_cache(maxsize=128)
                def decorator(func): return func

                # If used without arguments: @lru_cache
                if len(args) == 1 and callable(args[0]):
                    return args[0]

                return decorator

            try:
                # Try to attach it directly
                functools.lru_cache = mock_lru_cache
                functools.cache = mock_lru_cache  # htpy might use @cache too!
            except AttributeError:
                # Wrap it if functools is a read-only C module
                class FunctoolsWrapper:
                    lru_cache = staticmethod(mock_lru_cache)
                    cache = staticmethod(mock_lru_cache)
                    def __getattr__(self, name):
                        return getattr(functools, name)
                sys.modules["functools"] = FunctoolsWrapper()

        # 11. Polyfill Python 3.9 string methods into builtins
        import builtins
        def __removesuffix(s, suffix):
            if suffix and s.endswith(suffix): return s[:-len(suffix)]
            return s

        def __removeprefix(s, prefix):
            if prefix and s.startswith(prefix): return s[len(prefix):]
            return s

        builtins.__removesuffix = __removesuffix
        builtins.__removeprefix = __removeprefix

        # 12. Polyfill isinstance to intelligently handle Dummy Typing Objects
        import builtins
        _orig_isinstance = builtins.isinstance
        _orig_issubclass = builtins.issubclass

        def poly_isinstance(obj, class_or_tuple):
            try:
                # Real classes (str, BaseElement, int) evaluate perfectly here
                return _orig_isinstance(obj, class_or_tuple)
            except TypeError:
                # If we crash, we hit a dummy mock object!

                if _orig_isinstance(class_or_tuple, tuple):
                    return any(
                        poly_isinstance(obj, c) for c in class_or_tuple
                    )

                # In htpy's render loop, the ONLY mock
                # object it checks is `Iterable`.
                # So if we are here, it is simply asking:
                # "Can I iterate over this child node?"
                if (
                    hasattr(obj, "__iter__")
                    and not _orig_isinstance(obj, (str, bytes))
                ):
                    return True

                return False

        def poly_issubclass(cls, class_or_tuple):
            try:
                return _orig_issubclass(cls, class_or_tuple)
            except TypeError:
                if _orig_isinstance(class_or_tuple, tuple):
                    return any(poly_issubclass(cls, c) for c in class_or_tuple)
                return False

        builtins.poly_isinstance = poly_isinstance
        builtins.poly_issubclass = poly_issubclass
    # ---------------------------------------------------

    # Boot the application
    from pyplet.client import bootstrap_client
    await bootstrap_client(
        '{_APPS_VFS_ROOT}',
        '{project}',
        '{app}',
        {self.client_libraries},
    )
""")

        # Toggle between interpreters based on your class property
        script_tag = getattr(self, "interpreter", "py")

        py_config = {
            # `micropip` itself isn't auto-loaded by Pyodide; it must be
            # requested like any other package, or the runtime
            # `import micropip` in `bootstrap_client` (used to install
            # `self.client_libraries`) raises ModuleNotFoundError.
            "packages": (
                []
                if script_tag == "mpy"
                else ["htpy", "markupsafe", "micropip"]
            )
        }

        # Boot splash: a self-contained spinner shown inside #container from
        # the very first HTML response, covering the blank window while
        # PyScript/Pyodide and the transpiled app load. It carries no Tailwind
        # classes (Tailwind loads later, client-side) and no external assets —
        # only inline styles plus one <style> block for the rotation keyframes.
        # Apps that replace #container's contents (rather than appending to
        # them) drop it implicitly; bootstrap_client also removes
        # #pyplet-boot-splash by id once the app module has loaded, so apps
        # that append to #container don't leave it spinning. A fixed,
        # viewport-centered wrapper avoids any navbar-height assumption.
        boot_splash = markupsafe.Markup(  # nosec
            '<div id="pyplet-boot-splash" style="position:fixed;inset:0;'
            'display:flex;align-items:center;justify-content:center">'
            "<style>@keyframes pyplet-spin{to{transform:rotate(360deg)}}"
            "@media (prefers-reduced-motion:reduce)"
            "{#pyplet-boot-splash .pyplet-spinner{animation:none}}</style>"
            '<div class="pyplet-spinner" style="width:40px;height:40px;'
            "border:4px solid #dee2e6;border-top-color:#6c757d;"
            'border-radius:50%;animation:pyplet-spin 0.8s linear infinite">'
            "</div>"
            "</div>"
        )

        content = {
            "head": head_content,
            "body": [
                div(id="container")[boot_splash],
                markupsafe.Markup(  # nosec
                    f"<script type='{script_tag}' "
                    f"config='{json.dumps(py_config)}'"
                    f" async>{python_code}</script>"
                ),
            ],
        }

        tree = templates.application_template(
            f"{project}/{app}", handler, content
        )
        handler.write_html(tree)

    def routes(self) -> list[tuple[str, type, dict]]:
        """Return additional Tornado handlers contributed by this app.

        Each tuple is ``(url_regex, RequestHandlerClass, init_kwargs)`` —
        the same shape Tornado accepts in :class:`tornado.web.Application`'s
        ``handlers`` argument. Pyplet merges these into the global handler
        list at ``astart()`` time, inserted BEFORE the catch-all
        ``r"/.*"`` redirect so the routes are reachable. Default returns
        an empty list; apps that need custom HTTP routes (e.g. an
        asset-serving ``/apps/<project>/<app>/assets/...`` endpoint)
        override this.

        Tornado handler kwargs:
            Handlers that need app-scoped state (paths, caches, etc.)
            should accept those values via a Tornado ``initialize(...)``
            method and receive them as the third tuple element.

        Returns:
            Empty list by default. Override in subclasses to declare
            routes.

        Notes:
            - Pyplet invokes ``routes()`` ONCE per app at server startup,
              after the app instance has been registered via
              ``__init_subclass__``. The returned list is not re-read on
              subsequent requests.
            - Handlers added via ``routes()`` do NOT go through the
              ``_AuthMixin`` by default — auth-gated routes must explicitly
              subclass ``_AuthMixin`` from this module.
        """
        return []

    def __init_subclass__(cls):
        qualname = cls.__module__.split(".")
        if (
            qualname[0] == _APPS_MODULE_PREFIX
            and len(qualname) == 3
            and qualname[2].endswith("_server")
        ):
            _, project_name, app_name = qualname
            app_name = app_name.removesuffix("_server")

            server_applications[project_name, app_name] = cls()
