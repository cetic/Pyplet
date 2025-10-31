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
- `chat_client.py:31` uses `pyodide.create_proxy` to wire DOM events directly to the WebSocket.
- `chat_server.py:35` rebroadcasts every message to all connected clients.
- `chat_server.py:42` manages the user pool, removing sockets when clients disconnect.

This example demonstrates two-way real-time messaging with minimal boilerplate—ideal for exploring Pyplet’s WebSocket helpers.
