---
title: Desktop
---

# Example: Desktop

Simulates a desktop environment with draggable windows that load external pages. It mixes Pyplet’s DOM primitives with existing JavaScript widgets such as jQuery UI dialogs.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/desktop_*`
- Client entry point: `desktop_client.py`
- Server shim: `desktop_server.py`

Synchronise the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `desktop_client.py:8` builds dialog widgets through `pyplet.dom` before handing them to jQuery UI.
- `desktop_client.py:27` renders the full DOM tree and attaches per-window lifecycle hooks.
- `desktop_client.py:31` integrates with jQuery UI to provide draggable windows.
- `desktop_client.py:44` strips navigation chrome when embedding the main site into dialog iframes.

Use this example to see how Pyplet interoperates with existing JavaScript libraries while staying in Python.
