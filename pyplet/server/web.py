import asyncio
import os

import tornado
import tornado.web
import tornado.websocket

import pyplet
from pyplet.server import config

from .. import dom as d
from ..utils import get_import
from . import templates

__all__ = ["main"]


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache")


class PackageHandler(tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        app_config = get_import(f"{config.apps}.{project_name}.config")
        app_config.package(self)


class LoginHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write(d.render_html(templates.index_template(self)))


class AppHandler(tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        app_config = get_import(f"{config.apps}.{project_name}.config")
        content = app_config.serve(self)
        dom = templates.application_template(
            f"{project_name}/{app_name}", self, content=content
        )
        self.write(d.render_html(dom))


class ServerWebSocket(tornado.websocket.WebSocketHandler):
    closing_message = pyplet.WebSocket.closing_message

    async def open(self, project_name, app_name):
        server = get_import(f"{config.apps}.{project_name}.{app_name}_server")

        self.queue = asyncio.Queue()
        asyncio.create_task(server.websocket_server_loop(self))

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
                r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/([a-zA-Z_][a-zA-Z0-9_]*)\.zip",
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
        f"Listening to {config.url or f'http://{config.address}:{config.port}'}"
    )
    await asyncio.Event().wait()
