---
title: Server
---

# Server

Pyplet’s server runtime is built on top of Tornado and lives in the `pyplet.server` package:

- `pyplet.server.web` wires the HTTP routes, static assets, WebSocket endpoints and application shell.
- `pyplet.server.config` exposes configuration values such as address, port, apps root and the Pyodide URL.

The `pyplet start` [CLI](../cli.md) command configures `pyplet.server.config` (via command-line flags and `PYPLET_*` environment variables) and then starts the Tornado application defined in `pyplet.server.web`.

At a high level:

- The [home page](../index.md) lists micro apps discovered under the configured `apps` root.
- Each app is served via a dedicated route that loads Pyodide, fetches the app bundle, and calls `pyplet.client.bootstrap`.
- WebSocket endpoints expose a minimal async API compatible with `pyplet.WebSocket`, allowing apps to implement `websocket_server_loop` coroutines for real-time communication.

Refer to the [CLI](../cli.md) and [Micro Apps](../micro-apps.md) pages for details on configuration and app structure.
