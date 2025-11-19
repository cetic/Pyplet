import pyplet.dom as d
from pyplet.utils import get_import
import pyplet.server
from pyplet.server import config

import zipfile
import glob
import io
import os
from pathlib import Path


def package(handler: pyplet.server.web.PackageHandler):
    project, app = handler.path_args

    zip_bytes = io.BytesIO()
    pyplet_root = str(Path(pyplet.__file__).parent.parent)
    with zipfile.ZipFile(zip_bytes, "w") as zip_file:
        files = [
            (pyplet_root, "pyplet/client/**", ""),
            (pyplet_root, "pyplet/dom/**", ""),
            (pyplet_root, "pyplet/*.py", ""),
            (config.apps, f"{project}/**", "apps/"),
        ]
        for root_dir, pattern, prefix in files:
            for file in glob.glob(pattern, root_dir=root_dir, recursive=True):
                zip_file.write(os.path.join(root_dir, file), os.path.join(prefix, file))

    handler.set_header("Content-Type", "application/octet-stream")
    handler.write(zip_bytes.getvalue())


def serve(handler: pyplet.server.web.AppHandler):
    project, app = handler.path_args

    server = f"{handler.request.protocol}://{handler.request.host}"
    app_package = f"/apps/{project}/{app}.zip"

    client_libraries = getattr(
        get_import(f"{config.apps}.{project}.{app}_server"), "client_libraries", ()
    )

    return [
        d.head(
            d.script(src=f"https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js"),
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
                        await bootstrap({project!r}, {app!r}, {client_libraries!r})
                        
                    import asyncio
                    asyncio.create_task(main())
                `)
            }})();
            """
            ),
        ),
    ]
