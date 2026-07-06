---
title: Dashboard
---

# Example: Dashboard

A live monitoring panel that charts service activity with Matplotlib running in the browser via Pyodide. The server streams JSON, the client updates plots incrementally.

## Location

- Repository: `https://github.com/cetic/pyplet_examples`
- Path: `apps/pyplet_examples/examples/examples/dashboard_*`
- Client entry point: `dashboard_client.py`
- Server loop: `dashboard_server.py`

Pull the examples submodule if needed:

```bash
git submodule update --init --recursive
```

## Highlights

- `dashboard_client.py:17` seeds Matplotlib with historical series before the figure mounts in the DOM.

```python
if history is None:
    history = json.loads(await ws.receive())
    for l in history:
        (lines[l],) = plt.plot(history[l])
    plt.legend(list(history))
    plt.show()
    document.getElementById("container").appendChild(document.body.lastChild)
```

- `dashboard_client.py:28` ingests streamed JSON and mutates the plotted data in place.

```python
else:
    msg = await ws.receive()
    if msg is ws.closing_message:
        break
    live = json.loads(msg)
    for l in live:
        history[l].append(live[l])
        lines[l].set_ydata(history[l])
        lines[l].set_xdata(np.arange(len(history[l])))
```

- `dashboard_client.py:32` rescales the axes to keep recent data visible.

```python
plt.gca().relim()
plt.gca().autoscale_view()
plt.draw()
```

- `dashboard_server.py:23` samples metrics from sibling services.

```python
async def sample():
    while True:
        live = {
            "chat_server": len(chat_server.sockets),
            "numpy_server": len(numpy_server.sockets),
            "sync_numpy_server": len(sync_numpy_server.sockets),
            "dashboard_server": len(sockets),
        }
        async with sockets_lock:
            msg = json.dumps(live)
            exceptions = await asyncio.gather(
                *(s.send(msg) for s in sockets),
                return_exceptions=True,
            )
            for socket, exc in zip(sockets, exceptions):
                if exc:
                    sockets.remove(socket)
            for l in live:
                historical_data[l].append(live[l])
        await asyncio.sleep(1)
```

- `dashboard_server.py:45` pushes updates from a background coroutine.

```python
asyncio.create_task(sample())
```

Great for understanding how Pyplet handles streaming data and visualization stacks inside Pyodide.
