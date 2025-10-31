---
title: Dashboard
---

# Example: Dashboard

A live monitoring panel that charts service activity with Matplotlib running in the browser via Pyodide. The server streams JSON, the client updates plots incrementally.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/dashboard_*`
- Client entry point: `dashboard_client.py`
- Server loop: `dashboard_server.py`

Pull the examples submodule if needed:

```bash
git submodule update --init --recursive
```

## Highlights

- `dashboard_client.py:17` seeds Matplotlib with historical series before the figure mounts in the DOM.
- `dashboard_client.py:28` ingests streamed JSON and mutates the plotted data in place.
- `dashboard_client.py:32` rescales the axes to keep recent data visible.
- `dashboard_server.py:23` samples metrics from sibling services.
- `dashboard_server.py:45` pushes updates from a background coroutine.

Great for understanding how Pyplet handles streaming data and visualisation stacks inside Pyodide.
