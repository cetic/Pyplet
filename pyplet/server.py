import asyncio
import tornado
import tornado.web
import tornado.websocket
import os
import asyncio
import json

from .common.utils import get_import
from . import templates
from apps import config


__all__ = ["main"]


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache")


class PackageHandler(tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        config = get_import(f"apps.{project_name}.config")
        config.package(self)


class LoginHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write(templates.index_template(self).__html__())


class AppHandler(tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        config = get_import(f"apps.{project_name}.config")
        content = config.serve(self)
        dom = templates.application_template(
            f"{project_name}/{app_name}", self, content=content
        )
        self.write(dom.__html__())


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    async def open(self, project_name, app_name):
        server = get_import(f"apps.{project_name}.{app_name}_server")

        self.queue = asyncio.Queue()
        asyncio.create_task(server.websocket_server_loop(self))

    async def on_message(self, message):
        await self.queue.put(message)

    async def receive(self):
        return await self.queue.get()

    def send(self, message):
        return super().write_message(message, binary=not isinstance(message, str))

    def on_close(self):
        asyncio.get_running_loop().create_task(self.aclose())

    async def aclose(self):
        await self.queue.put(StopIteration)


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
                {"path": os.path.join(os.path.dirname(__file__), "../pyodide")},
            ),
            (r"/", LoginHandler),
            (r"/apps/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)\.zip", PackageHandler),
            (r"/apps/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+).ws", WebSocketHandler),
            (r"/apps/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)", AppHandler),
            (r"/.*", tornado.web.RedirectHandler, {"url": "/", "permanent": False}),
        ],
        debug=config.debug,
    )


async def amain():
    app = make_app()

    app.listen(config.port, config.address)
    print(f"Listening to {config.url}")
    await asyncio.Event().wait()


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
