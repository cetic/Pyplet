---
title: Sync Slider
---

# Example: Sync Slider

A collaborative slider powered by jQuery UI where every connected browser sees
the same value in real time.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/sync_slider_*`
- Client entry point: `sync_slider_client.py`
- Server loop: `sync_slider_server.py`

Fetch the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `sync_slider_client.py:22` mounts a jQuery UI slider and wraps DOM callbacks
  with `create_proxy_with_this` plus `asyncio.create_task` so Pyodide can fire
  WebSocket writes without blocking the UI thread.

```python
def init_slider(value: int, ws: pyplet.WebSocket) -> None:
    params = {
        "value": value,
        "slide": utils.create_proxy_with_this(
            lambda this, event, ui: asyncio.create_task(ws.send(str(ui.value)))
        ),
    }
    slider.slider(utils.to_js_obj(params))
    container.append(slider)
```

- `sync_slider_client.py:31` handles remote broadcasts, updating the slider UI
  whenever another user moves it.

```python
async def websocket_client_loop(ws: pyplet.WebSocket):
    value = await ws.receive()
    if value is ws.closing_message:
        return

    init_slider(int(value), ws)

    while True:
        v = await ws.receive()
        if v is ws.closing_message:
            break
        slider.slider("value", int(v))
```

- `sync_slider_server.py:28` welcomes newcomers with the latest slider value
  and `sync_slider_server.py:36` fans out subsequent updates to every connected
  peer.

```python
async def websocket_server_loop(ws: pyplet.WebSocket) -> None:
    clients.append(ws)
    global value
    await ws.send(str(value))

    while True:
        v = await ws.receive()
        if v is ws.closing_message:
            break

        value = int(v)
        await asyncio.gather(
            *(client.send(str(value)) for client in clients if client is not ws)
        )

    clients.remove(ws)
```

Use this example when you need a minimal template for synchronising form
controls across multiple clients.
