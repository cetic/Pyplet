---
title: Sync NumPy
---

# Example: Sync NumPy

A broadcast variant of the NumPy stream where every viewer shares the same frame feed. Demonstrates coordinated fan-out with background tasks.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/pyplet_examples/sync_numpy_*`
- Client entry point: `sync_numpy_client.py`
- Server loop: `sync_numpy_server.py`

Fetch the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `sync_numpy_client.py:1` reuses the standard NumPy client loop to stay aligned with the shared feed.

```python
from .numpy_client import websocket_client_loop
```

- `sync_numpy_server.py:17` spawns a background task that keeps generating and broadcasting frames.

```python
async def send_to_all():
    while True:
        if sockets:
            bytes = io.BytesIO()
            array = np.random.randn(10, 10)
            np.save(bytes, array)
            value = bytes.getvalue()
            for ws in list(sockets):
                try:
                    await ws.send(value)
                except tornado.websocket.WebSocketClosedError:
                    sockets.remove(ws)
        await asyncio.sleep(1)

asyncio.create_task(send_to_all())
```

- `sync_numpy_server.py:24` prunes disconnected sockets while iterating the subscriber set.

```python
for ws in list(sockets):
    try:
        await ws.send(value)
    except tornado.websocket.WebSocketClosedError:
        sockets.remove(ws)
```

Start here when you need a baseline for multi-client synchronised streams.
