---
title: Sync NumPy
---

# Example: Sync NumPy

A broadcast variant of the NumPy stream where every viewer shares the same frame feed. Demonstrates coordinated fan-out with background tasks.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/sync_numpy_*`
- Client entry point: `sync_numpy_client.py`
- Server loop: `sync_numpy_server.py`

Fetch the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `sync_numpy_client.py:1` reuses the standard NumPy client loop to stay aligned with the shared feed.
- `sync_numpy_server.py:17` spawns a background task that keeps generating and broadcasting frames.
- `sync_numpy_server.py:24` prunes disconnected sockets while iterating the subscriber set.

Start here when you need a baseline for multi-client synchronised streams.
