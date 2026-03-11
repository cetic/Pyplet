import glob
import io
import os
import zipfile
from pathlib import Path

from markupsafe import Markup

import pyplet.server
from pyplet.dom import div, link, script
from pyplet.server import config
from pyplet.utils import get_import


def package(handler: pyplet.server.web.PackageHandler):
    """Package the app before serving it"""
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
                zip_file.write(
                    os.path.join(root_dir, file), os.path.join(prefix, file)
                )

    handler.set_header("Content-Type", "application/octet-stream")
    handler.write(zip_bytes.getvalue())


def serve(handler: pyplet.server.web.AppHandler):
    project, app = handler.path_args

    server = f"{handler.request.protocol}://{handler.request.host}"  # noqa: E501, F841
    app_package = f"/apps/{project}/{app}.zip"

    client_libraries = getattr(
        get_import(f"{config.apps}.{project}.{app}_server"),
        "client_libraries",
        (),
    )

    return {
        "head": [
            script(
                src="https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js"
            ),
            link(
                rel="stylesheet",
                href="https://code.jquery.com/ui/1.14.1/themes/base/jquery-ui.css",  # noqa: E501
            ),
            script(src="https://code.jquery.com/jquery-3.7.1.min.js"),
            script(src="https://code.jquery.com/ui/1.14.1/jquery-ui.min.js"),
        ],
        "body": [
            div(id="container"),
            script(type="text/javascript")[
                Markup(f"""
            (async function() {{
                let pyodide = await loadPyodide({{
                }});
                pyodide.runPython(`
                    async def main():
                        from js import fetch

                        response = await fetch('{app_package}')
                        response = await response.arrayBuffer()
                        response = response.to_py().tobytes()

                        import io, zipfile
                        zip_file = zipfile.ZipFile(io.BytesIO(response), 'r')
                        zip_file.extractall()
                        from pyplet.client import bootstrap
                        await bootstrap(
                            '{project}',
                            '{app}',
                            {client_libraries},
                        )

                    import asyncio
                    asyncio.create_task(main())
                `)
            }})();
            """)
            ],
        ],
    }
