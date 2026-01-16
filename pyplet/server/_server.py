import asyncio
import tornado
import tornado.web
import tornado.websocket
import os
import asyncio
import json
import sys
from pathlib import Path
import io
import zipfile
import glob
from importlib import import_module
import runpy

from . import templates
from ..shared import dom as d
import pyplet
from pyplet.server import config
from typing import Dict, Tuple


server_applications: Dict[Tuple[str, str], "ServerApplication"] = {}


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache")


class PackageHandler(tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        application = server_applications[project_name, app_name]
        application.package(self)


class LoginHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write(d.render_html(templates.index_template(self)))


class AppHandler(tornado.web.RequestHandler):
    async def get(self, project_name, app_name):
        application = server_applications[project_name, app_name]
        application.serve(self)


class ServerWebSocket(tornado.websocket.WebSocketHandler):
    closing_message = pyplet.WebSocket.closing_message

    async def open(self, project_name, app_name):
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
            (r"/.*", tornado.web.RedirectHandler, {"url": "/", "permanent": False}),
        ],
        debug=config.debug == "1",
    )


async def astart():
    app = make_app()
    app.listen(config.port, config.address)
    for path in glob.glob(f"{config.apps}/*/*_server.py"):
        module_name = path[:-3].replace("/", ".")
        import_module(module_name)
    print(f"Listening to {config.url or f'http://{config.address}:{config.port}'}")

    await asyncio.Event().wait()


class ServerApplication:
    title: str = None
    deps = ()
    identifier: Tuple[str, str] = None

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
            await bootstrap({config.apps!r}, {project!r}, {app!r}, {self.deps!r})
            
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
            and qualname[-1].endswith("_server")
        ):
            _, project_name, app_name = qualname
            app_name = app_name.removesuffix("_server")

            server_applications[project_name, app_name] = cls()
