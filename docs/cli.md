---
title: CLI
---

# Command-Line Usage

Pyplet ships a CLI entry point named `pyplet`. It provides subcommands to scaffold new apps and start the server.

## `pyplet init`

Initialize a new micro app under the `apps/` directory:

```bash
pyplet init <project_name>
```

This creates:

- `apps/<project_name>/<project_name>_client.py`
- `apps/<project_name>/<project_name>_server.py`
- `apps/<project_name>/config.py`

The generated app is a generic micro-app template that you can adapt to your own use case.

## `pyplet start`

Start the Pyplet server and serve apps discovered under `apps/`:

```bash
pyplet start
```

By default, configuration values are loaded from `pyplet.server.config`, which in turn reads environment variables. You can override any of these settings via CLI options:

- `--address`: bind address (default `127.0.0.1`)
- `--port`: listen port (default `8080`)
- `--url`: URL advertised in logs; if not set, derived from address/port
- `--apps`: root folder where apps live (default `apps`)
- `--pyodide-url`: URL to the Pyodide JavaScript bundle (defaults to a Pyodide CDN URL)
- `--debug`: enable or disable Tornado debug mode (boolean flag)

For example:

```bash
pyplet start --address 0.0.0.0 --port 9999 --debug 0
```

Once started, the server prints the listening URL. Open it in your browser to reach the Pyplet [home page](index.md).

## Environment variables

The same parameters can also be supplied via environment variables, which are read by `pyplet.server.config` before CLI overrides:

- `PYPLET_ADDR`
- `PYPLET_PORT`
- `PYPLET_URL`
- `PYPLET_APPS`
- `PYPLET_PYODIDE`
- `PYPLET_DEBUG`

For everyday usage it is often enough to rely on the defaults and override only a subset of options either via flags or environment variables.

## Advanced: custom apps root

By default, Pyplet looks for applications under the `apps/` folder. You can point it to a different directory by changing the apps root:

- Via CLI:

  ```bash
  pyplet start --apps src/apps
  ```

- Via environment variable:

  ```bash
  PYPLET_APPS=src/apps pyplet start
  ```

This is useful when integrating Pyplet into an existing project layout while still keeping the micro-app structure and discovery logic intact.
