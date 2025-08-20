import pyplet.common.cdn_imports as cdn_imports
import pyplet.common.dom as d
from pyplet.common.utils import get_import
import pyplet.server
from . import dashboard_server

import zipfile
import glob
import io
import os


def package(handler: pyplet.server.PackageHandler):
    project, app = handler.path_args

    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zip_file:
        files = [
            (os.path.dirname(os.path.dirname(pyplet.__file__)), "pyplet/client/**"),
            (os.path.dirname(os.path.dirname(pyplet.__file__)), "pyplet/common/**"),
            (os.getcwd(), f"apps/{project}/**"),
        ]
        for root_dir, pattern in files:
            for file in glob.glob(pattern, root_dir=root_dir, recursive=True):
                zip_file.write(os.path.join(root_dir, file), file)

    handler.set_header("Content-Type", "application/octet-stream")
    handler.write(zip_bytes.getvalue())


def serve(handler: pyplet.server.AppHandler):
    project, app = handler.path_args

    server = f"{handler.request.protocol}://{handler.request.host}"
    app_package = f"/apps/{project}/{app}.zip"

    client_libraries = getattr(
        get_import(f"apps.{project}.{app}_server"), "client_libraries", ()
    )

    return [
        d.head(
            d.script(src=f"{server}/pyodide/pyodide.js"),
        ),
        d.body(
            d.div(id="container"),
            d.script(type="text/javascript").append(
                f"""
            (async function() {{
                let pyodide = await loadPyodide({{
                    indexURL : "{server}/pyodide/"
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
                        from pyplet.client.v0 import bootstrap
                        await bootstrap({project!r}, {app!r}, {client_libraries!r})
                        
                    import asyncio
                    asyncio.create_task(main())
                `)
            }})();
            """
            ),
        ),
    ]
