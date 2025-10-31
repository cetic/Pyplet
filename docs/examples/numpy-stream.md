---
title: NumPy Stream
---

# Example: NumPy Stream

Streams random matrices from the server to the browser and visualises them as heatmaps. Showcases binary frame transport and incremental plotting.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/numpy_*`
- Client entry point: `numpy_client.py`
- Server loop: `numpy_server.py`

Initialise or refresh the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `numpy_client.py:12` deserialises NumPy arrays from WebSocket frames.
- `numpy_client.py:14` seeds a live `imshow` plot that updates in place.
- `numpy_client.py:18` animates by mutating the existing image buffer.
- `numpy_server.py:15` generates random matrices every second.
- `numpy_server.py:18` sends binary payloads directly to all connected clients.

Great when you need a template for transporting binary data or streaming scientific visualisations.
