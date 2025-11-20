---
title: Welcome to Pyplet
---

# Pyplet

Serve interactive web applications entirely in Python. Pyplet couples a Tornado backend with a Pyodide-powered client runtime, so you can write browser code, DOM manipulation, plotting, and real‑time messaging without leaving Python.

![Pyplet Home](assets/homepage.jpg)

Key capabilities:

- Pure Python on both sides: Tornado on the server, Pyodide in the browser
- Simple micro app structure and packaging model
- WebSockets for real-time, async interactions
- Works with scientific Python packages in the browser (e.g., NumPy, Matplotlib)

Get started in minutes:

```bash
# Create a virtual environment (Python 3.13+)
uv venv --python 3.13
source .venv/bin/activate

# Install Pyplet in editable mode
pip install -e .  # local checkout

# Install example dependencies (optional)
# Examples are not bundled; clone them first, then install their deps
uv sync --group examples

# Create a new micro app
pyplet init my_app

# Run the server and serve apps under ./apps
pyplet start
```

Then open http://127.0.0.1:8080 to browse available apps.

Next steps:

- Follow [Getting Started](getting-started.md) to configure assets and explore the example apps
- See [Examples](examples/index.md) to clone the examples repo and tour the available micro-apps
- See [Micro Apps](micro-apps.md) for app structure and packaging details
- Try the Tutorials ([Frontend-only](tutorials/frontend-only.md), [WebSocket](tutorials/websocket-app.md)) to build your first apps end to end
- Browse the [API Reference](api/dom.md) for the [DOM DSL](api/dom.md), [client bootstrap](api/bootstrap.md), and [server internals](api/server.md)
