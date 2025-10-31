---
title: Micro Apps
---

# Micro Apps

Pyplet organizes applications as small, focused micro apps. Each app lives under `apps/<project>/` and consists of:

- A `<name>_client.py` module executed in the browser via Pyodide
- A `<name>_server.py` module running on Tornado
- A `config.py` per project with `package(handler)` and `serve(handler)` helpers

## Files and responsibilities

Client module (`*_client.py`):

- Optional `client_init()` coroutine for initial page setup
- Optional `websocket_client_loop(ws)` coroutine to process messages using a Pyplet WebSocket protocol
- DOM rendering with the `pyplet.dom` DSL and browser interop via `pyodide.ffi` and `js`

Server module (`*_server.py`):

- Optional `client_libraries`: list of Pyodide packages to install (e.g., `numpy`, `matplotlib`)
- Optional `websocket_server_loop(ws)`: async server loop that exchanges text or binary frames

Packaging (`apps/<project>/config.py`):

- `package(handler)`: builds an app zip with the client runtime and app sources
- `serve(handler)`: returns a DOM tree that loads Pyodide, unpacks the app zip, and calls `pyplet.client.bootstrap()`

```python
--8<-- "apps/pyplet_examples/config.py"
```

## URLs

- Home: `/` lists apps discovered under `apps/*/*_client.py`
- App: `/apps/<project>/<name>` renders the app container
- Bundle: `/apps/<project>/<name>.zip` serves the packaged client bundle
- WebSocket: `/apps/<project>/<name>.ws` is the server-side WebSocket endpoint

## Client libraries (Pyodide)

Any additional Python packages used by the client don’t need pre-installation. Declare them in the server file as `client_libraries`, and Pyodide installs them at runtime.

The **Examples** section of the documentation walks through concrete micro-apps that apply these patterns—real-time chat, dashboards, canvas-based playgrounds, and more. Start there when you want a guided tour of fully working apps.
