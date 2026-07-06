---
title: Examples
---

# Examples Overview

Pyplet does not bundle the official examples by default. To run the reference micro-apps locally, first fetch the examples repository and install the optional dependencies.

## Fetch and install

```bash
# Clone the examples into your local checkout
git clone https://github.com/cetic/pyplet_examples apps/pyplet_examples

# Install dependencies used by the examples
uv sync --group examples

# Launch the server and browse the examples
pyplet start
```

Then open <http://127.0.0.1:8080> to see the examples under **Apps**.

!!! note "Updating an existing checkout"
    If you already have the repository, pull latest changes with `git -C apps/pyplet_examples pull`. If your project tracks the examples as a submodule, run `git submodule update --init --recursive` instead of cloning.

## Available examples

- [Chat](chat.md): multi-user WebSocket chat with no JavaScript
- [Dashboard](dashboard.md): server-side plotting and layout composition
- [Desktop](desktop.md): desktop-like window management in the browser
- [Frontend Only](frontend-only.md): browser-only app running entirely in Pyodide
- [Gradient Descent Playground](gradient-descent-playground.md): interactive parameter tuning for optimization
- [NumPy Stream](numpy-stream.md): streaming NumPy arrays to update plots in real time
- [Sync NumPy](sync-numpy.md): synchronized array updates between client and server
- [Sync Slider](sync-slider.md): shared state between UIs connected via WebSocket
