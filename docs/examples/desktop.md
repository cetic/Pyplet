---
title: Desktop
---

# Example: Desktop

Simulates a desktop environment with draggable windows that load external pages. It mixes Pyplet’s DOM primitives with existing JavaScript widgets such as jQuery UI dialogs.

## Location

- Repository: `https://github.com/cetic/pyplet_examples`
- Path: `apps/pyplet_examples/examples/examples/desktop_*`
- Client entry point: `desktop_client.py`
- Server shim: `desktop_server.py`

Synchronise the examples submodule:

```bash
git submodule update --init --recursive
```

## Highlights

- `desktop_client.py:8` builds dialog widgets through `pyplet.dom` before handing them to jQuery UI.

```python
@create_proxy
def new_window(e):
    tree = d.div(title="text").append(
        d.iframe(
            src="/",
            frameborder="0",
            style="overflow:hidden;height:100%;width:100%",
            width="100%",
            height="100%",
        )
    )
```

- `desktop_client.py:27` renders the full DOM tree and attaches per-window lifecycle hooks.

```python
    div = tree._render_dom(document)
    container.appendChild(div)
    iframe = div.firstChild
    iframe.addEventListener("load", on_load)
```

- `desktop_client.py:31` integrates with jQuery UI to provide draggable windows.

```python
    jQ(container.lastChild).dialog({"width": 800, "height": 600}).on(
        "dialogclose", close
    )
```

- `desktop_client.py:44` strips navigation chrome when embedding the main site into dialog iframes.

```python
@create_proxy
def on_load(event):
    jQ(".navbar", event.target.contentDocument).remove()
    jQ(".footer", event.target.contentDocument).remove()
    jQ(".ui-dialog-title", jQ(event.target.parentNode).closest(".ui-dialog")).text(
        event.target.contentDocument.title
    )
```

Use this example to see how Pyplet interoperates with existing JavaScript libraries while staying in Python.
