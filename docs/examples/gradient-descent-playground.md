---
title: GradientDescentPlayground
---

# Example: GradientDescentPlayground

This demo lives in a separate repository and can be included under `apps/` in two ways.

## Option 1: Git submodule (recommended)

```bash
git submodule add git@git.cetic.be:seglab/gradientdescentplayground.git apps/GradientDescentPlayground
git submodule update --init --recursive
```

To update later:

```bash
cd apps/GradientDescentPlayground
git pull origin main  # or the appropriate default branch
```

## Option 2: Plain clone (quick local setup)

```bash
git clone git@git.cetic.be:seglab/gradientdescentplayground.git apps/GradientDescentPlayground
```

## Launching the demo

Start the Pyplet server and open:

```
http://127.0.0.1:8888/apps/GradientDescentPlayground/GradientDescentPlayground
```

Notes:

- The final URL segment must match the `_client`/`_server` filename prefix inside the demo folder
- If the demo declares extra `client_libraries`, Pyodide installs them automatically on first load

