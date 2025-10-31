---
title: Frontend-only App
---

# Tutorial: Frontend-only App

In this tutorial, you’ll build a client-only app that:

- Renders a simple DOM tree in the browser
- Uses NumPy and Matplotlib via Pyodide

## Client code

We can reuse the included example as a template and adapt it later:

```python
--8<-- "apps/pyplet_examples/frontend_only_client.py"
```

## Server stub

Because this app runs entirely in the browser, the server component just declares client libraries so the bundle brings NumPy and Matplotlib:

```python
--8<-- "apps/pyplet_examples/frontend_only_server.py"
```

## Run it

Start the server and navigate to the URL shown on the home page for the “frontend_only” app.

That’s it — you’ve built a fully client-side experience entirely in Python.
