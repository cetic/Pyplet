---
title: CLI
---

# Command-Line Usage

Pyplet doesn’t ship a console script yet. Use the Python module entrypoint to run the server:

```bash
python -m pyplet.server
```

Configuration is loaded from `apps/config.py`:

```python
--8<-- "apps/config.py"
```

Once started, the server prints the listening URL. Open it in your browser to reach the Pyplet home page.

