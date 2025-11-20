---
title: WebSocket App
---

# Tutorial: WebSocket App

Let’s build a real-time app that exchanges messages between browser and server using Pyplet’s WebSocket protocol. We’ll use the [chat example](../examples/chat.md) as a reference.

## Client: handling input and messages

```python
--8<-- "apps/pyplet_examples/chat_client.py"
```

The client:

- Renders a text input and listens for changes
- Sends messages over the socket and appends new messages to the DOM
- Handles the server closing by checking for the `closing_message` sentinel

## Server: broadcasting to all clients

```python
--8<-- "apps/pyplet_examples/chat_server.py"
```

The server loop:

- Assigns a username from a pool and sends an init handshake
- Broadcasts messages to all connected sockets
- Cleans up on disconnect

## Run it

Start the server and open multiple browser tabs to the chat app’s URL. You should see messages broadcast in real-time.
