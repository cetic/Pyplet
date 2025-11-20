---
title: Troubleshooting
---

# Troubleshooting

!!! note "Browser support"
    Prefer a Chromium‑based browser (Chrome, Edge, Brave). Other browsers generally work, but some graphics (e.g., canvas/Matplotlib) and behaviors may differ or degrade.

- Pyodide assets not loading
  - By default, Pyplet loads Pyodide from a public CDN. Check that your network allows access to the configured `PYPLET_PYODIDE` URL or the value passed via `--pyodide-url`.
  - If you use a self-hosted Pyodide bundle, ensure it is reachable by the browser and that the `pyodide_url` setting points to the correct location.

- Port already in use
  - Change `--port` (or `PYPLET_PORT`) or stop the conflicting process

- WebSocket closes immediately
  - Check browser console and server logs
  - Ensure client/server message types match (text vs binary)

- Matplotlib figures not visible
  - After `plt.show()`, target the figure node and append it to your container (see examples which use `document.body.lastChild`)
