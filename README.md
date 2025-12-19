# Pyplet

Pyplet is an application server meant to serve interactive web applications entirely written in Python.

> Note: For the best results when viewing and interacting with Pyplet apps, use a Chromium‑based browser (Chrome, Edge, Brave). Other browsers are supported, but some graphical elements or behaviors may differ, or even look/perform poorly.

## Installation

Clone the repository and create a Python ≥ 3.11 virtual environment **before** installing Pyplet in editable mode. We recommend using `uv`, but any equivalent tool is fine.

```bash
git clone git@git.cetic.be:seglab/pyplet.git
cd pyplet
uv venv --python 3.11  # or newer
source .venv/bin/activate
```

Once the environment is active you can install Pyplet and the optional example dependencies.

```bash
pip install -e .
uv sync --group examples  # optional, installs extra packages used by sample apps
```

By default, Pyplet loads the Pyodide runtime from a public CDN, so no manual Pyodide download is required for local development.

## Creating and running apps

Pyplet organizes applications under an `apps/` folder at the project root. To scaffold a new micro app, use the CLI:

```bash
pyplet init <project_name>
```

This command creates a neutral micro-app template under `apps/<project_name>/` with:

- `<project_name>_client.py`: browser-side code running in Pyodide
- `<project_name>_server.py`: server-side WebSocket loop
- `config.py`: packaging and HTML shell helpers

Once you have at least one app under `apps/`, start the server with:

```bash
pyplet start
```

Each application folder under `apps/` must provide:

- A `<name>_client.py` module executed in Pyodide (define `client_init` and any browser logic).
- A matching `<name>_server.py` module; for client-only apps it at least declares `client_libraries` (Pyodide packages to install) and `websocket_client_loop`.
- A `config.py` file exposing `package(handler)` and `serve(handler)` functions that bundle the app and render the HTML shell.
- Any additional Python packages used by the app do **not** need to be pre-installed with `pip`; list them in `client_libraries` and Pyodide will install them on demand. See the catalogue of compatible packages at https://pyodide.org/en/stable/usage/packages-in-pyodide.html.

Once the server is running, browse to `http://127.0.0.1:8080` to reach the Pyplet home page listing available apps.

![Pyplet home page](homepage.jpg)

You can navigate directly to a specific app via `http://127.0.0.1:8080/apps/<project>/<name>` where `<project>` is the folder inside `apps/` (for example `examples`) and `<name>` matches the `_client`/`_server` filename prefix.

## Examples

Pyplet ships with a curated catalogue of micro-apps that demonstrate real-time messaging, plotting, desktop-style layouts, and optimization playgrounds. These examples live in a dedicated repository:

`git@git.cetic.be:seglab/pyplet_examples.git`

This repository vendors the examples under `apps/pyplet_examples/`. If that folder is missing, clone the `pyplet_examples` repository into it.

All server parameters can also be supplied via `PYPLET_*` environment variables (see the CLI documentation for details).

See the [Examples section of the documentation](docs/examples/) for a tour of the available micro-apps and instructions on how to build your own.
