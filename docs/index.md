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

# Install the project in editable mode
pip install -e .

# Install example dependencies (optional)
uv sync --group examples

# Run the server
python -m pyplet.server
```

Then open http://127.0.0.1:8888 to browse available apps.

Next steps:

- Follow Getting Started to configure assets and explore the example apps
- See Micro Apps for app structure and packaging details
- Try the Tutorials to build your first frontend-only app and a WebSocket app
- Browse the API Reference for the DOM DSL, client bootstrap, and server internals

