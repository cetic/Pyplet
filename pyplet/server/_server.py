import asyncio
import base64
import glob
import gzip
import json
import logging
import os
import secrets
import textwrap
from importlib import import_module
from pathlib import Path
from typing import Dict, Optional, Tuple

import tornado
import tornado.web
import tornado.websocket
from markupsafe import Markup

import pyplet
from pyplet.server import config

from ..shared.dom import div, link, script
from . import magiclink, oauth, templates

# Configure logging
logger = logging.getLogger("pyplet.server")


server_applications: Dict[Tuple[str, str], "ServerApplication"] = {}


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


class AboutHandler(_AuthMixin, tornado.web.RequestHandler):
    """
    GET  /about  — show the about page.
    """

    async def get(self):
        user = self._require_auth()
        if user is None:
            return
        self.write(str(templates.about_template(self, user)).encode("UTF-8"))


class PackageHandler(_AuthMixin, tornado.web.RequestHandler):
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


class LoginHandler(_AuthMixin, tornado.web.RequestHandler):
    """
    GET  /login  — show login page (provider buttons) or redirect to / if
                   already authenticated.
    """

    async def get(self):
        if oauth.auth_enabled() and oauth.get_session(self) is not None:
            self.redirect("/")
            return
        self.write(str(templates.login_template(self)).encode("UTF-8"))


class IndexHandler(_AuthMixin, tornado.web.RequestHandler):
    """
    GET  /  — show the index page with the apps the user is allowed to see.
    """

    async def get(self):
        user = self._require_auth()
        if user is None:
            return
        self.write(str(templates.index_template(self, user)).encode("UTF-8"))


class LogoutHandler(tornado.web.RequestHandler):
    async def get(self):
        oauth.clear_session(self)
        self.redirect("/")


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


class AppHandler(_AuthMixin, tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        user = self._require_auth(project_name, app_name)
        if user is None:
            return
        application = server_applications[project_name, app_name]
        application.serve(self)


class ServerWebSocket(_AuthMixin, tornado.websocket.WebSocketHandler):
    closing_message = pyplet.WebSocket.closing_message
    _is_ws = True

    async def open(self, project_name, app_name):
        user = self._require_auth(project_name, app_name)
        if user is None:
            self.close(1008, "Unauthorized")
            return

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
            r"/static/(.*)",
            tornado.web.StaticFileHandler,
            {"path": os.path.join(os.path.dirname(__file__), "static")},
        ),
        (
            r"/pyodide/(.*)",
            tornado.web.StaticFileHandler,
            {"path": os.path.join(os.path.dirname(__file__), "../pyodide")},
        ),
        (r"/", IndexHandler),
        (r"/about", AboutHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/oauth/login", OAuthLoginHandler),
        (r"/oauth/callback", OAuthCallbackHandler),
        (r"/auth/email", MagicLinkRequestHandler),
        (r"/auth/verify", MagicLinkVerifyHandler),
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
}


async def astart():
    app = tornado.web.Application(**_app_spec)
    app.listen(config.port, config.address)

    # Load all server applications
    server_modules = glob.glob(f"{config.apps}/*/*_server.py")
    for path in server_modules:
        module_name = path[:-3].replace("/", ".")
        try:
            import_module(module_name)
            logger.debug(f"Loaded module: {module_name}")
        except Exception as e:
            logger.error(
                f"Failed to load module {module_name}: {e}", exc_info=True
            )

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

        file_map = {}
        files = [
            (pyplet_root, "pyplet/*", ""),
            (pyplet_root, "pyplet/shared/**", ""),
            (pyplet_root, "pyplet/client/**", ""),
            (".", f"{config.apps}/{project}/**", ""),
        ]

        for root_dir, pattern, prefix in files:
            for file in glob.glob(pattern, root_dir=root_dir, recursive=True):
                full_path = os.path.join(root_dir, file)
                if not os.path.isfile(full_path):
                    continue

                target_path = os.path.join(prefix, file)

                # Read as bytes and encode to base64 for JSON safety
                with open(full_path, "rb") as f:
                    encoded_content = base64.b64encode(f.read()).decode(
                        "utf-8"
                    )
                    file_map[target_path] = encoded_content

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
        app_package = f"/apps/{project}/{app}.json"

        # Inject PyScript core scripts
        head_content = [
            link(
                rel="stylesheet",
                href="https://pyscript.net/releases/2024.1.1/core.css",
            ),
            script(
                type="module",
                src="https://pyscript.net/releases/2024.1.1/core.js",
            ),
            link(
                rel="stylesheet",
                href="https://code.jquery.com/ui/1.14.1/themes/base/jquery-ui.css",  # noqa: E501
            ),
            script(src="https://code.jquery.com/jquery-3.7.1.min.js"),
            script(src="https://code.jquery.com/ui/1.14.1/jquery-ui.min.js"),
        ]

        # The Python script to run on the client
        # (works in both Pyodide and MicroPython)
        python_code = textwrap.dedent(f"""
            import base64
            import os
            import json
            import sys
            from js import fetch

            # Polyfill os.makedirs
            def ensure_dir(path):
                if not path: return
                parts = path.split("/")
                current_path = ""
                for part in parts:
                    if not part: continue

                    current_path = current_path + "/"
                    current_path += part if current_path else part

                    try:
                        os.mkdir(current_path)
                    except OSError:
                        pass

            # Top-level await for the package
            response = await fetch('{app_package}')

            if not response.ok:
                print(f"Failed to fetch package: HTTP {{response.status}}")
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

                # --- NEW: Mock the typing module for MicroPython ---
                if sys.implementation.name == "micropython":
                    # 1. Mock Typing
                    if "typing" not in sys.modules:
                        class MockTyping:
                            def __getattr__(self, name): return self
                            def __getitem__(self, key): return self
                        sys.modules["typing"] = MockTyping()

                    # 2. Polyfill importlib
                    if "importlib" not in sys.modules:
                        class MockImportlib:
                            @staticmethod
                            def import_module(name, package=None):
                                # Handle basic relative imports
                                # if they exist in your framework
                                if name.startswith('.'):
                                    if not package:
                                        raise TypeError(
                                            "Relative imports require"
                                            " the 'package' argument"
                                        )
                                    # Very basic resolution
                                    # (assumes 1 level deep like '.my_module')
                                    name = package + name

                                # Passing a fromlist like ['']
                                # forces __import__ to return
                                # the rightmost module
                                return __import__(
                                    name, globals(), locals(), ['']
                                )

                        sys.modules["importlib"] = MockImportlib()
                # ---------------------------------------------------

                # Boot the application
                from pyplet.client import bootstrap_client
                await bootstrap_client(
                    '{config.apps}',
                    '{project}',
                    '{app}',
                    {self.client_libraries},
                )
        """)

        # Toggle between interpreters based on your class property
        script_tag = getattr(self, "interpreter", "py")

        content = {
            "head": head_content,
            "body": [
                div(id="container"),
                Markup(
                    f'<script type="{script_tag}" async>{python_code}</script>'
                ),
            ],
        }

        tree = templates.application_template(
            f"{project}/{app}", handler, content
        )
        handler.write(str(tree).encode("UTF-8"))

    def __init_subclass__(cls):
        qualname = cls.__module__.split(".")
        if (
            qualname[0] == config.apps
            and len(qualname) == 3
            and qualname[2].endswith("_server")
        ):
            _, project_name, app_name = qualname
            app_name = app_name.removesuffix("_server")

            server_applications[project_name, app_name] = cls()
