---
title: Getting Started
---

# Getting Started

This guide gets you up and running locally with Pyplet.

## Prerequisites

- Python 3.13 or newer
- A virtual environment tool (e.g., `uv`, `venv`, or `virtualenv`)

!!! note "Browser support"
    For the best experience, use a Chromium‑based browser (Chrome, Edge, Brave). Other browsers are compatible, but some graphical elements or behaviors may differ, or in some cases look or perform poorly.

## Install Pyplet

```bash
uv venv --python 3.13
source .venv/bin/activate
pip install -e .
```

Optionally install example dependencies used by the bundled demo apps:

```bash
uv sync --group examples
```

## Pyodide runtime assets

Pyplet serves the Pyodide runtime under `/pyodide/`. Make sure the Pyodide bundle is available under `pyplet/pyodide/` (see project README for the exact steps you use internally). Once present, the server can serve the runtime to clients.

## Run the server

Start the Tornado server:

```bash
python -m pyplet.server
```

Visit http://127.0.0.1:8888 to see the home page with available apps.

Server settings live in `apps/config.py`:

```python
--8<-- "apps/config.py"
```

- `address`: bind address
- `port`: listen port
- `url`: convenience string for logging
- `debug`: Tornado debug mode

## Explore examples

Open any app by navigating to `/apps/<project>/<name>` where `<project>` is the folder under `apps/` (e.g., `examples`) and `<name>` matches the `_client`/`_server` filename prefix.

Examples include:

- Chat (real-time broadcast with WebSockets)
- NumPy heatmap stream (binary frames + Matplotlib)
- Dashboard (live chart of service connections)
- Frontend-only app (Pyodide + Matplotlib + DOM)
