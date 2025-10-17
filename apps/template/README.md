# Pyplet Example Apps

Pyplet couples a Tornado backend with Pyodide-powered clients so you can write full-stack apps in pure Python. The micro apps in this folder showcase how Pyplet bridges browser DOM APIs, plotting libraries, and WebSockets to build interactive experiences quickly.

## Chat (`chat_client.py`, `chat_server.py`)
- Real-time multi-user chat driven entirely by async WebSocket loops.
- Demonstrates server-side user pooling and broadcast messaging plus DOM updates directly from Python.
- `chat_client.py:26` decodes the initial handshake so the UI can announce the assigned username.
- `chat_client.py:31` wraps the DOM change event with `create_proxy` to send WebSocket messages straight from Python.
- `chat_server.py:35` repackages incoming text and `chat_server.py:42` fan-outs the payload to every connected peer.

## Dashboard (`dashboard_client.py`, `dashboard_server.py`)
- Live monitoring panel that charts connection counts from other example services.
- Highlights streaming JSON over WebSockets into Matplotlib figures rendered in the browser.
- `dashboard_client.py:17` draws historical series into Matplotlib lines before the figure is mounted inside the DOM.
- `dashboard_client.py:28` streams live JSON updates, mutating line data and rescaling the axes (`dashboard_client.py:32`).
- `dashboard_server.py:23` samples connection counts from other services, while `dashboard_server.py:45` keeps a background task pushing updates.

## Desktop (`desktop_client.py`, `desktop_server.py`)
- Simulates a desktop environment with detachable windows loading the main site.
- Mixes `pyplet.dom` primitives with jQuery UI dialogs to show interop with existing JS widgets.
- `desktop_client.py:8` builds a dialog with an iframe mounted via `pyplet.dom`, reproducing desktop-like windows.
- `desktop_client.py:27` renders the Pyplet DOM tree into the browser and wires `on_load` for each popup.
- `desktop_client.py:31` hands control to jQuery UI dialogs, and `desktop_client.py:44` strips navigation chrome from the embedded page.

## Frontend Only (`frontend_only_client.py`, `frontend_only_server.py`)
- Fully client-side demo that still leverages NumPy and Matplotlib via Pyodide.
- Shows how to package additional libraries with `client_libraries` without needing a Python server loop.
- `frontend_only_client.py:6` composes the page entirely with `pyplet.dom` from the browser context.
- `frontend_only_client.py:12` and `frontend_only_client.py:14` use NumPy plus Matplotlib in Pyodide to plot locally.
- `frontend_only_server.py:1` declares the extra client libraries so the bundle ships scientific tooling without a Python backend.

## Numpy Stream (`numpy_client.py`, `numpy_server.py`)
- Streams random matrices from the server and draws them as heatmaps.
- Illustrates binary data transfer over WebSockets and live figure updates.
- `numpy_client.py:12` deserializes `np.load` buffers from WebSocket frames and `numpy_client.py:14` seeds a live `imshow`.
- `numpy_client.py:18` updates the image in-place for smooth animation as data arrives.
- `numpy_server.py:15` creates random matrices each second and `numpy_server.py:18` streams the raw bytes to clients.

## Sync Numpy (`sync_numpy_client.py`, `sync_numpy_server.py`)
- Broadcast version of the NumPy stream where every viewer shares the same feed.
- Uses a background task to push frames to all connected clients, demonstrating fan-out patterns.
- `sync_numpy_client.py:1` reuses the regular NumPy client loop to stay in sync with the shared feed.
- `sync_numpy_server.py:17` launches a background task that continually generates frames for all viewers.
- `sync_numpy_server.py:24` iterates active sockets safely, removing disconnected clients during broadcast.

These samples are meant to be launched through Pyplet’s packaging machinery (`config.py`). Start from any of them to explore how Pyplet keeps Python code running fluidly on both sides of the wire.
