# Pyplet

**Build full-stack web applications entirely in Python.**

Pyplet is an application server that lets you create interactive web applications using Python on both the client and server side. Powered by [Pyodide](https://pyodide.org/) (Python compiled to WebAssembly), Pyplet brings the full power of Python to the browser.

## Why Pyplet?

- **Pure Python**: Write your entire application in Python - no JavaScript required
- **Real-time Communication**: Built-in WebSocket support for seamless client-server interaction
- **Modern Async**: Leverages Python's async/await for responsive applications
- **Browser-Native**: Client code runs directly in the browser via WebAssembly
- **Shared Code**: Reuse Python modules between client and server

## Quick Start

### Prerequisites

- Python ≥3.12
- `uv` (recommended) or `pip`

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd pyplet
   ```

2. **Download Pyodide** (optional - for local development)
   
   Pyplet uses Pyodide from CDN by default. For offline development, download it locally:
   ```bash
   wget https://github.com/pyodide/pyodide/releases/download/0.29.0/pyodide-0.29.0.tar.bz2
   tar -xvjf pyodide-0.29.0.tar.bz2
   ```
   
   Then configure Pyplet to use the local version:
   ```bash
   export PYPLET_PYODIDE=/path/to/pyodide/pyodide.js
   ```

3. **Install Pyplet**

   With `uv` (recommended):
   ```bash
   uv venv
   uv sync
   ```

   Or with `pip`:
   ```bash
   pip install -e .
   ```
   
   To install with test dependencies:
   ```bash
   uv sync --extra test
   # or with pip
   pip install -e .[test]
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

**`hello_client.py`** (runs in the browser):
```python
import pyplet
from js import document

container = document.getElementById("container")

class _(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        # Receive message from server
        message = await ws.receive()
        container.innerText = message.decode()
        
        # Send message back to server
        await ws.send(b"Hello from the browser!")
```

**`hello_server.py`**:
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

## How It Works

Pyplet uses a unique dual-runtime architecture:

1. **Server-side**: Standard CPython running Tornado web server
2. **Client-side**: Python code compiled to WebAssembly via Pyodide, running in the browser
3. **Communication**: WebSocket connection bridges the two environments

```
┌─────────────────────┐         WebSocket         ┌─────────────────────┐
│   Browser (Pyodide) │ <───────────────────────> │   Server (CPython)  │
│   your_app_client.py│                           │   your_app_server.py│
└─────────────────────┘                           └─────────────────────┘
```

## Project Structure

```
pyplet/
├── apps/              # Your applications live here
│   └── template/      # Template for new projects
├── pyplet/
│   ├── server/        # Server-side framework
│   ├── client/        # Client-side framework
│   └── shared/        # Code shared between client & server
│       ├── websocket.py  # WebSocket abstraction
│       └── dom/          # DOM manipulation utilities
├── pyproject.toml     # Project configuration
└── README.md          # You are here
```

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

# Start server with custom options
pyplet start --port 3000 --address 0.0.0.0

# Run server directly with Python
python -m pyplet.server
```

## Configuration

Server-wide configuration is managed in `pyplet/server/config.py` and can be set via environment variables or CLI flags:

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

## Browser Compatibility

Pyplet should work in any modern browser that supports WebAssembly:
- Chrome/Edge 57+
- Firefox 52+
- Safari 11+

## Dependencies

Pyplet uses:
- **Tornado** - Async web server
- **Pyodide** - Python in WebAssembly
- **Cython** - Python to C compiler for performance
- **pyodide-build** - Build tools for Pyodide packages

## Adding Dependencies

### For server-side code:
Edit `pyproject.toml` under `[project].dependencies`

### For testing:
Edit `pyproject.toml` under `[project.optional-dependencies].test`

## Examples

Check the `apps/template/` directory for a working example demonstrating:
- WebSocket communication
- DOM manipulation
- Async patterns
- Client-server interaction

## Limitations

Since client code runs in Pyodide (WebAssembly):
- Not all Python packages are available in the browser
- Some stdlib modules have limited functionality
- Use the `js` module to access browser APIs directly

## Contributing

Contributions are welcome! When contributing:

1. Maintain clean separation between client and server code
2. Use async/await for all I/O operations
3. Test in both server (CPython) and client (Pyodide) environments
4. Follow the existing naming conventions

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details

## Support

- **Author**: Maxime Istasse (istassem@gmail.com)
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
