---
title: Getting Started
---

# Getting Started

This guide gets you up and running locally with Pyplet.

## Prerequisites

- Python 3.12 or newer
- A virtual environment tool (e.g., `uv`, `venv`, or `virtualenv`)

!!! note "Browser support"
    For the best experience, use a Chromium‑based browser (Chrome, Edge, Brave). Other browsers are compatible, but some graphical elements or behaviors may differ, or in some cases look or perform poorly.

## Install Pyplet

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install pyplet
```

All server parameters can also be supplied via `PYPLET_*` environment variables (see the [CLI](cli.md) page for details).

## Pyodide runtime assets

By default, Pyplet loads Pyodide from a public CDN. You do not need to download the Pyodide bundle manually for local development.

Advanced setups can override the Pyodide URL (for example to point to a self-hosted bundle) via the `--pyodide-url` option documented in the [CLI](cli.md) page or the `PYPLET_PYODIDE` environment variable.

## Run the server

Start the Tornado server:

```bash
pyplet start
```

Visit <http://127.0.0.1:8080> to see the [home page](index.md) with available apps.

Server settings live in `pyplet.server.config` and can be overridden either via CLI flags or environment variables. Refer to the [CLI](cli.md) documentation for the full list of options.

## Create a new app

To scaffold a new micro app under `apps/`, run:

```bash
pyplet init <project_name>
```

This creates a generic template under `apps/<project_name>/` that you can adapt to your use case.

## Explore examples

Open any app by navigating to `/apps/<project>/<name>` where `<project>` is the folder under `apps/` (e.g., `examples`) and `<name>` matches the `_client`/`_server` filename prefix.

The official examples repository lives at `https://github.com/cetic/pyplet_examples`. In this project, examples are available under `apps/pyplet_examples/examples/`; if that folder is missing, clone the `pyplet_examples` repository into it. Refer to [Examples](examples/index.md) for cloning instructions and a full tour of the available micro-apps.
