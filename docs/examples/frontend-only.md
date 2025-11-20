---
title: Frontend Only
---

# Example: Frontend Only

A purely client-side application that still leverages NumPy and Matplotlib through Pyodide. No Python runs on the server once the bundle loads.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/pyplet_examples/frontend_only_*`
- Client entry point: `frontend_only_client.py`
- Server shim: `frontend_only_server.py`

Pull the examples submodule after cloning:

```bash
git submodule update --init --recursive
```

## Highlights

- `frontend_only_client.py:6` builds the entire layout with `pyplet.dom` from the browser context.

```python
tree = d.div(
        d.p("This is a frontend-only app."),
        d.p("Yet, it can leverage matplotlib, numpy, ... ", "How cool is that?"),
)
document.getElementById("container").appendChild(tree._render_dom(document))
```

- `frontend_only_client.py:12` and `frontend_only_client.py:14` generate plots with NumPy and Matplotlib inside Pyodide.

```python
x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.plot(x, y)
plt.show()
document.getElementById("container").appendChild(document.body.lastChild)
```

- `frontend_only_server.py:1` declares required `client_libraries`, demonstrating how to bundle scientific packages for frontend use.

```python
client_libraries = ["matplotlib", "numpy"]
```

This example is ideal when experimenting with fully offline Pyodide experiences that still use Python’s scientific stack.
