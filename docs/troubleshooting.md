---
title: Troubleshooting
---

# Troubleshooting

!!! note "Browser support"
    Prefer a Chromium‑based browser (Chrome, Edge, Brave). Other browsers generally work, but some graphics (e.g., canvas/Matplotlib) and behaviors may differ or degrade.

- Pyodide assets not found
  - Ensure the Pyodide bundle is present under `pyplet/pyodide/` and is accessible by the server

- Port already in use
  - Change `port` in `apps/config.py` or stop the conflicting process

- WebSocket closes immediately
  - Check browser console and server logs
  - Ensure client/server message types match (text vs binary)

- Matplotlib figures not visible
  - After `plt.show()`, target the figure node and append it to your container (see examples which use `document.body.lastChild`)
