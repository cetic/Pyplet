---
title: NumPy Stream
---

# Example: NumPy Stream

Streams random matrices from the server to the browser and visualises them as heatmaps. Showcases binary frame transport and incremental plotting.

## Location

- Repository: `https://github.com/cetic/pyplet_examples`
- Path: `apps/pyplet_examples/examples/numpy_*`
- Client entry point: `numpy_client.py`
- Server loop: `numpy_server.py`

Initialise or refresh the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `numpy_client.py:12` deserialises NumPy arrays from WebSocket frames.

```python
array = np.load(io.BytesIO(await ws.receive()))
```

- `numpy_client.py:14` seeds a live `imshow` plot that updates in place.

```python
if im is None:
        im = fig.gca().imshow(array, vmin=-4, vmax=4)
        plt.show()
        document.getElementById("container").appendChild(document.body.lastChild)
```

- `numpy_client.py:18` animates by mutating the existing image buffer.

```python
else:
        im.set_data(array)
        plt.draw()
```

- `numpy_server.py:15` generates random matrices every second.

```python
array = np.random.randn(10, 10)
np.save(bytes, array)
await asyncio.sleep(1)
```

- `numpy_server.py:18` streams the serialized bytes back to the connected client.

```python
try:
        await ws.send(bytes.getvalue())
except tornado.websocket.WebSocketClosedError:
        break
```

Great when you need a template for transporting binary data or streaming scientific visualisations.
