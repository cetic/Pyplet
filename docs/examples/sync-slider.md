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
- `sync_slider_client.py:31` handles remote broadcasts, updating the slider UI
  whenever another user moves it.
- `sync_slider_server.py:28` welcomes newcomers with the latest slider value
  and `sync_slider_server.py:36` fans out subsequent updates to every connected
  peer.

Use this example when you need a minimal template for synchronising form
controls across multiple clients.
