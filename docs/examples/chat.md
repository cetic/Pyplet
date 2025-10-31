---
title: Chat
---

# Example: Chat

A multi-user chat room powered entirely by Pyplet. Messages arrive over WebSockets, the UI updates through Pyodide DOM calls, and no JavaScript is required.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/chat_*`
- Client entry point: `chat_client.py`
- Server loop: `chat_server.py`

Fetch or refresh the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `chat_client.py:26` unwraps the handshake payload to display the assigned username.

  ```python
  async def websocket_client_loop(ws: pyplet.WebSocket):
      init = decode(await ws.receive())
      assert init["type"] == "init"
      render(f"<b>Logged in as {init['name']}</b>")
  ```

- `chat_client.py:31` uses `pyodide.create_proxy` to wire DOM events directly to the WebSocket.

  ```python
      @create_proxy
      async def submit(_):
          message = input.value
          input.value = ""
          await ws.send(message)

      input.addEventListener("change", submit)
  ```

- `chat_server.py:35` rebroadcasts every message to all connected clients.

  ```python
      while True:
          msg = await ws.receive()
          if msg is ws.closing_message:
              break
          msg = json.dumps({"type": "message", "name": name, "message": msg})
          await asyncio.gather(*(s.send(msg) for s in sockets.values()))
  ```

- `chat_server.py:42` manages the user pool, removing sockets when clients disconnect.

  ```python
      del sockets[name]
      available.insert(0, name)
  ```

This example demonstrates two-way real-time messaging with minimal boilerplate—ideal for exploring Pyplet’s WebSocket helpers.
