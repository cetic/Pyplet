"""Pyplet server web module."""

import asyncio
import os

import tornado
import tornado.web
import tornado.websocket

import pyplet
from pyplet.server import config

from ..utils import get_import
from . import templates

__all__ = ["main"]  # noqa: F822


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


class PackageHandler(tornado.web.RequestHandler):
    """A handler for serving package resources."""

    async def get(self, project_name: str, app_name: str) -> None:
        """Serves a package resource for the given project and app.

        Args:
            project_name (str): The name of the project.
            app_name (str): The name of the app.
        """
        app_config = get_import(f"{config.apps}.{project_name}.config")
        app_config.package(self)


class LoginHandler(tornado.web.RequestHandler):
    """A handler for serving the login page."""

    async def get(self):
        """Serves the login page.

        Args:
            project_name (str): The name of the project.
            app_name (str): The name of the app.
        """
        self.write(str(templates.index_template(self)).encode("utf-8"))


class AppHandler(tornado.web.RequestHandler):
    """A handler for serving the app page."""

    async def get(self, project_name: str, app_name: str):
        """Serves the app page.

        Args:
            project_name (str): The name of the project.
            app_name (str): The name of the app.
        """
        app_config = get_import(f"{config.apps}.{project_name}.config")
        content = app_config.serve(self)
        dom = templates.application_template(
            f"{project_name}/{app_name}", self, content=content
        )
        self.write(str(dom).encode("utf-8"))


class AboutHandler(tornado.web.RequestHandler):
    """A handler for serving the about page."""

    async def get(self):
        """Serves the about page."""
        dom = templates.about_template(self)
        self.write(str(dom).encode("utf-8"))


class ServerWebSocket(tornado.websocket.WebSocketHandler):
    closing_message = pyplet.WebSocket.closing_message

    async def open(self, project_name: str, app_name: str):
        """Opens the WebSocket connection."""
        server = get_import(f"{config.apps}.{project_name}.{app_name}_server")

        self.queue = asyncio.Queue()
        asyncio.create_task(server.websocket_server_loop(self))

    async def on_message(self, message):
        """Receives a message from the client."""
        await self.queue.put(message)

    async def receive(self):
        """Receives a message from the client."""
        return await self.queue.get()

    async def send(self, message):
        """Sends the given message to the client of this Web Socket."""
        await super().write_message(
            message, binary=not isinstance(message, str)
        )

    def on_close(self):
        """Closes the WebSocket by sending the closing message."""
        asyncio.get_running_loop().create_task(self.aclose())

    async def aclose(self):
        """Closes the WebSocket by sending the closing message."""
        await self.queue.put(self.closing_message)


def make_app():
    return tornado.web.Application(
        [
            (
                r"/static/(.*)",
                tornado.web.StaticFileHandler,
                {"path": os.path.join(os.path.dirname(__file__), "static")},
            ),
            (
                r"/pyplet/client/(.*)",
                StaticFileHandler,
                {"path": os.path.join(os.path.dirname(__file__), "client")},
            ),
            (
                r"/pyplet/common/(.*)",
                StaticFileHandler,
                {"path": os.path.join(os.path.dirname(__file__), "common")},
            ),
            (
                r"/pyodide/(.*)",
                tornado.web.StaticFileHandler,
                {
                    "path": os.path.join(
                        os.path.dirname(__file__), "../pyodide"
                    )
                },
            ),
            (r"/", LoginHandler),
            (
                r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/"
                r"([a-zA-Z_][a-zA-Z0-9_]*)\.zip",
                PackageHandler,
            ),
            (
                r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*).ws",
                ServerWebSocket,
            ),
            (
                r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*)",
                AppHandler,
            ),
            (
                r"/about",
                AboutHandler,
            ),
            (
                r"/.*",
                tornado.web.RedirectHandler,
                {"url": "/", "permanent": False},
            ),
        ],
        debug=config.debug == "1",
    )


async def astart():
    app = make_app()
    app.listen(config.port, config.address)
    print(
        "Listening to "
        f"{config.url or f'http://{config.address}:{config.port}'}"
    )
    await asyncio.Event().wait()
