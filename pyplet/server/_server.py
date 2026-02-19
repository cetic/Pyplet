import asyncio
import tornado
import tornado.web
import tornado.websocket
import os
import asyncio
import json
import secrets
import sys
from pathlib import Path
import io
import zipfile
import glob
from importlib import import_module
import runpy
import logging

from . import templates
from . import oauth
from . import magiclink
from ..shared import dom as d
import pyplet
from pyplet.server import config
from typing import Dict, Tuple

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

    def _require_auth(self, project: str | None = None, app: str | None = None):
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
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache")


# ---------------------------------------------------------------------------
# Application handlers
# ---------------------------------------------------------------------------


class PackageHandler(_AuthMixin, tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
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
        self.write(d.render_html(templates.login_template(self)))


class IndexHandler(_AuthMixin, tornado.web.RequestHandler):
    """
    GET  /  — show the index page with the apps the user is allowed to see.
    """

    async def get(self):
        user = self._require_auth()
        if user is None:
            return
        self.write(d.render_html(templates.index_template(self, user)))


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
    GET  /auth/verify?token=<token>  — validates the token and logs the user in.
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
        await super().write_message(message, binary=not isinstance(message, str))

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
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/oauth/login", OAuthLoginHandler),
        (r"/oauth/callback", OAuthCallbackHandler),
        (r"/auth/email", MagicLinkRequestHandler),
        (r"/auth/verify", MagicLinkVerifyHandler),
        (
            r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*)\.zip",
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
        (r"/.*", tornado.web.RedirectHandler, {"url": "/", "permanent": False}),
    ],
    "debug": config.debug == "1",
    # Signs session cookies.  Falls back to a per-process random value so the
    # server still works without PYPLET_COOKIE_SECRET (sessions lost on restart).
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
            logger.error(f"Failed to load module {module_name}: {e}", exc_info=True)

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
    title: str = None
    client_libraries: Tuple[str] = ()
    mcp_tools = ()

    def websocket_server_loop(self, websocket: tornado.websocket.WebSocketHandler): ...

    def package(self, handler: PackageHandler):
        project, app = handler.path_args

        zip_bytes = io.BytesIO()
        pyplet_root = str(Path(pyplet.__file__).parent.parent)
        with zipfile.ZipFile(zip_bytes, "w") as zip_file:
            files = [
                (pyplet_root, "pyplet/*", ""),
                (pyplet_root, "pyplet/shared/**", ""),
                (pyplet_root, "pyplet/client/**", ""),
                (".", f"{config.apps}/{project}/**", ""),
            ]
            for root_dir, pattern, prefix in files:
                for file in glob.glob(pattern, root_dir=root_dir, recursive=True):
                    if not os.path.isfile(os.path.join(root_dir, file)):
                        continue
                    zip_file.write(
                        os.path.join(root_dir, file), os.path.join(prefix, file)
                    )

        handler.set_header("Content-Type", "application/octet-stream")
        handler.write(zip_bytes.getvalue())

    def serve(self, handler: AppHandler):
        project, app = handler.path_args

        server = f"{handler.request.protocol}://{handler.request.host}"
        app_package = f"/apps/{project}/{app}.zip"

        content = [
            d.head(
                d.script(
                    src=f"https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js"
                ),
                d.link(
                    rel="stylesheet",
                    href="https://code.jquery.com/ui/1.14.1/themes/base/jquery-ui.css",
                ),
                d.script(src="https://code.jquery.com/jquery-3.7.1.min.js"),
                d.script(src="https://code.jquery.com/ui/1.14.1/jquery-ui.min.js"),
            ),
            d.body(
                d.div(id="container"),
                d.script(type="text/javascript").append(
                    f"""
(async function() {{
    let pyodide = await loadPyodide({{
    }});
    pyodide.runPython(`
        async def main():
            from js import fetch

            response = await fetch({app_package!r})
            response = await response.arrayBuffer()
            response = response.to_py().tobytes()

            import io, zipfile
            zip_file = zipfile.ZipFile(io.BytesIO(response), 'r')
            zip_file.extractall()
            from pyplet.client import bootstrap
            await bootstrap({config.apps!r}, {project!r}, {app!r}, {self.client_libraries!r})
            
        import asyncio
        asyncio.create_task(main())
    `)
}})();
"""
                ),
            ),
        ]

        tree = templates.application_template(f"{project}/{app}", handler, content)
        handler.write(d.render_html(tree))

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
