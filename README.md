# Pyplet

**Build full-stack web applications entirely in Python.**

Pyplet is an application server that lets you create interactive web
applications using Python on both the client and server side.
Powered by [PyScript](https://pyscript.net/) (Python compiled to WebAssembly),
Pyplet brings the full power of Python to the browser.

## Why Pyplet?

- **Pure Python**: Write your entire application in Python - no JavaScript required
- **Real-time Communication**: Built-in WebSocket support for seamless
client-server interaction
- **Modern Async**: Leverages Python's `async`/`await` for responsive applications
- **Browser-Native**: Client code runs directly in the browser via WebAssembly
- **Shared Code**: Reuse Python modules between client and server

## Quick Start

### Prerequisites

- Python ≥3.12
- `uv` (recommended) or `pip`

### Installation

The recommended way to install Pyplet is via uv.

1. Install venv

    ```bash
    uv venv
    ```

1. Activate the venv

    ```bash
    source ./venv/bin/activate
    ```

1. Install Pyplet

    ```bash
    uv pip install pyplet
    ```

### Create Your First App

```bash
pyplet init my_app
```

This creates a new project in `apps/my_app/` with two files:

- `my_app_client.py` - Python code that runs in the browser
- `my_app_server.py` - Server-side Python logic

### Run the Server

```bash
pyplet start
```

Then open your browser to `http://localhost:8080` to see your apps!

## Example Application

Here's a minimal Pyplet app showing real-time communication:

**`hello_client.py`**, runs in the browser:

```python
import pyplet
from js import document

container = document.getElementById("container")

class MyClientApp(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        # Receive message from server
        message = await ws.receive()
        container.innerText = message.decode()

        # Send message back to server
        await ws.send(b"Hello from the browser!")
```

**`hello_server.py`**, runs on the server:

```python
import pyplet

class _(pyplet.server.ServerApplication):
    async def websocket_server_loop(self, ws: pyplet.WebSocket):
        # Send message to client
        await ws.send(b"Hello from the server!")

        # Receive client's response
        response = await ws.receive()
        print(f"Client says: {response.decode()}")
```

## Custom GUI components

You can create reusable components that work on both client and server.

### Download Component

```python
# Server side download component
download("./static/static_file.txt", "Download from server"),

# Client side download component (from virtual file system, i.e., from_vfs=True)
download(
    "./public/vfs_file.txt", "Download from client", from_vfs=True
),
```

You must put you files in the right project folder in the `static` directory
 (the name of the directory must be `static`)
for the server, and in the `public` directory for the client
 (the name of the directory can be changed, but should not be `static`).
The `from_vfs` flag tells Pyplet to look for the file in the virtual file
system (client-side) instead of the server's filesystem.

## How It Works

Pyplet uses a unique dual-runtime architecture:

1. **Server-side**: Standard CPython running Tornado web server
2. **Client-side**: Python code compiled to WebAssembly
(e.g., via PyScript using Pyodide), running in the browser
3. **Communication**: WebSocket connection bridges the two environments

```text
┌──────────────────────┐         WebSocket         ┌───────────────────────┐
│  Browser (PyScript)  │ <───────────────────────> │   Server (CPython)    │
│  your_app_client.py  │                           │   your_app_server.py  │
└──────────────────────┘                           └───────────────────────┘
```

## Project Structure

```bash
apps/                     # Your apps live here
├── auth_rules.json       # The authentification rules are defined here
└── app_1/
    ├── app_1_client.py   # The client code
    └── app_1_server.py   # The server code
```

## Authentication

Pyplet supports platform-level OAuth2 / OIDC authentication via Google and
Microsoft. When enabled, all pages and WebSocket connections are gated behind
a login screen. Auth is **opt-in**: if no provider is configured the platform
runs with no login, exactly as before.

### Setup

**1. Register an OAuth app** with your provider and obtain a client ID and
secret. Set the callback URL to:

[http://\<your-host>/oauth/callback](http://\<your-host>/oauth/callback)

**2. Set environment variables:**

```bash
# Required to sign session cookies (generate once and keep it stable):
export PYPLET_COOKIE_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# Google
export OAUTH_GOOGLE_CLIENT_ID=your-client-id
export OAUTH_GOOGLE_CLIENT_SECRET=your-client-secret

# Microsoft / Entra ID (can be set alongside Google)
export OAUTH_MICROSOFT_CLIENT_ID=your-client-id
export OAUTH_MICROSOFT_CLIENT_SECRET=your-client-secret
export OAUTH_MICROSOFT_TENANT=common  # or your tenant ID
```

**3. Start the server** — a login page with provider buttons appears automatically.

### Access control (ACL)

By default every authenticated user can see all apps. To restrict access,
create `apps/auth_rules.json` — a JSON array of
`["project/app regex", "email regex"]` pairs:

```json
[
    [".*",           "@mycompany\\.com$"],
    ["public/demo",  ".*"]
]
```

Rules are evaluated in order; the **first matching rule** grants access.
The first regex is matched against the combined `"project/app"` string;
the second against the user's email address.
If no rule matches, access is denied.

Override the rules file path with `PYPLET_AUTH_RULES_FILE`.

### Magic-link e-mail authentication

As an alternative (or complement) to OAuth, users can sign in by entering their
e-mail address and clicking a single-use link delivered to their inbox — no
password required.

Configure an SMTP server to enable it:

```bash
export MAGICLINK_SMTP_HOST=smtp.example.com
export MAGICLINK_SMTP_PORT=587          # default
export MAGICLINK_SMTP_USER=noreply@example.com
export MAGICLINK_SMTP_PASSWORD=secret
export MAGICLINK_FROM=noreply@example.com   # optional, defaults to SMTP_USER
export MAGICLINK_TOKEN_TTL=900              # seconds (default: 15 min)
# Set to "0" to disable STARTTLS (not recommended):
# export MAGICLINK_SMTP_TLS=0
```

Magic-link and OAuth providers can be active simultaneously — the login page
shows all available methods.

The ACL rules file applies to magic-link logins exactly the same way it does
for OAuth: the user's e-mail address is matched against the `email_regex`
column of each rule.

### Configuration reference

| Variable | Description |
| --- | --- |
| `PYPLET_COOKIE_SECRET` | Secret for signing session cookies |
| **OAuth — Google** | |
| `OAUTH_GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `OAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |
| **OAuth — Microsoft** | |
| `OAUTH_MICROSOFT_CLIENT_ID` | Microsoft / Entra ID client ID |
| `OAUTH_MICROSOFT_CLIENT_SECRET` | Microsoft / Entra ID client secret |
| `OAUTH_MICROSOFT_TENANT` | Tenant ID or `common` (default: `common`) |
| **Magic-link** | |
| `MAGICLINK_SMTP_HOST` | SMTP server hostname (required to enable magic-link) |
| `MAGICLINK_SMTP_PORT` | SMTP port (default: `587`) |
| `MAGICLINK_SMTP_USER` | SMTP login username |
| `MAGICLINK_SMTP_PASSWORD` | SMTP login password |
| `MAGICLINK_SMTP_TLS` | Use STARTTLS: `1` (default) or `0` for plain SMTP |
| `MAGICLINK_FROM` | Sender address (defaults to `MAGICLINK_SMTP_USER`) |
| `MAGICLINK_TOKEN_TTL` | Token validity in seconds (default: `900` = 15 min) |
| **ACL** | |
| `PYPLET_AUTH_RULES_FILE` | ACL rules path (default: `apps/auth_rules.json`) |

## Advanced Features

### DOM Manipulation

Pyplet provides utilities for working with the DOM:

```python
from pyplet.shared.dom import create_element

# Create elements programmatically
button = create_element('button', {'class': 'btn btn-primary'}, 'Click me!')
```

### Bootstrap Components

Built-in support for Bootstrap UI components:

```python
from pyplet.shared.dom.bootstrap import create_button, create_card

button = create_button('Primary', style='primary')
card = create_card('Card Title', 'Card content goes here')
```

### Environment Detection

Check whether code is running on server or client:

```python
import pyplet

if pyplet.is_server:
    print("Running on server")

elif pyplet.is_client:
    print("Running in browser")
```

## CLI Reference

```bash
# Create a new project
pyplet init <project_name>

# Start the development server
pyplet start
pyplet run
pyplet server

# Start server with custom options
pyplet start --port 3000 --address 0.0.0.0

# Start the tutorial
pyplet tutorial

# Run server directly with Python
python -m pyplet.server
```

## Configuration

Server-wide configuration is managed in `pyplet/server/config.py` and can be
set via environment variables or CLI flags:

```bash
# Using environment variables
export PYPLET_PORT=3000
export PYPLET_ADDRESS=0.0.0.0
pyplet start

# Using CLI flags
pyplet start --port 3000 --address 0.0.0.0
```

Available configuration options:

- `--address` / `PYPLET_ADDR` - Server address (default: `127.0.0.1`)
- `--port` / `PYPLET_PORT` - Server port (default: `8080`)
- `--apps` / `PYPLET_APPS` - Apps directory (default: `apps`)
- `--debug` / `PYPLET_DEBUG` - Debug mode (default: `1`)
- `--pyodide-url` / `PYPLET_PYODIDE` - Pyodide CDN URL
- `--url` / `PYPLET_URL` - Custom URL override

See the [Authentication](#authentication) section for OAuth-related variables.

## Browser Compatibility

Pyplet should work in any modern browser that supports WebAssembly:

- Chrome/Edge 57+
- Firefox 52+
- Safari 11+

## Dependencies

Pyplet uses:

- **Tornado** - Async web server
- **PyScript** - Python in WebAssembly (via Pyodide)
- **Cython** - Python to C compiler for performance

## Adding Dependencies

### For server-side code

Edit `pyproject.toml` under `[project].dependencies`

### For testing

Edit `pyproject.toml` under `[project.optional-dependencies].test`

## Examples

Check the `apps/template/` directory for a working example demonstrating:

- WebSocket communication
- DOM manipulation
- Async patterns
- Client-server interaction

## Limitations

Since client code runs in PyScript (WebAssembly):

- Not all Python packages are available in the browser
- Some stdlib modules have limited functionality
- The `js` module gives direct access to the browser APIs

## Contributing

Contributions are welcome! When contributing:

1. Maintain clean separation between client and server code
2. Use `async`/`await` for all I/O operations
3. Test in both server (CPython) and client (PyScript) environments
4. Follow the existing naming conventions
5. Use the `prek` (`pre-commit`)
6. Implement tests for the features your are adding

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details

## Support

- **Authors**:
  - Maxime Istasse (<istassem@gmail.com>)
  - Arthur Lorin (<arthur.lorin@cetic.be>)
  - Erwan Henin (<erwan.henin@cetic.be>)
  - Vincent Stragier (<vincent.stragier@cetic.be>)

- **Issues**: Please report bugs and feature requests via the issue tracker

## Roadmap

Future enhancements planned:

- Hot reload during development
- More built-in UI components
- Better error handling and debugging tools
- Enhanced documentation and tutorials
- Package distribution via PyPI

---

**Happy coding with Python everywhere!** 🐍✨
