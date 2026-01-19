# AGENTS.md - Welcome AI Agents!

Welcome to the Pyplet repository! This guide is designed to help AI coding agents quickly understand the codebase structure, architecture, and development patterns.

## Project Overview

**Pyplet** is an application server for building interactive web applications entirely in Python, powered by Pyodide (Python compiled to WebAssembly). It enables full-stack Python development where both client and server code are written in Python.

## Architecture

### Core Concept
Pyplet uses a client-server architecture where:
- **Server**: Standard Python (CPython) running Tornado web server
- **Client**: Python code running in the browser via Pyodide/WebAssembly
- **Communication**: WebSocket-based bidirectional messaging

### Key Components

```
pyplet/
├── server/          # Server-side components (CPython)
│   ├── _server.py   # Tornado server implementation
│   ├── cli.py       # CLI commands (init, start)
│   ├── config.py    # Server configuration
│   └── templates.py # HTML template generation
├── client/          # Client-side components (Pyodide)
│   ├── __init__.py  # ClientApplication base class
│   └── utils.py     # Client utilities
├── shared/          # Shared between client and server
│   ├── websocket.py # WebSocket abstraction
│   └── dom/         # DOM manipulation utilities
│       ├── _dom.py      # Core DOM API
│       └── bootstrap.py # Bootstrap components
└── __init__.py      # Environment detection (server vs client)
```

## Code Patterns

### Application Structure
Each Pyplet app consists of two files:
1. `{app_name}_server.py` - Server-side logic
2. `{app_name}_client.py` - Client-side logic (runs in browser)

Example client application:
```python
import pyplet
from js import document

class _(pyplet.client.ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        # Receive message from server
        message = await ws.receive()
        # Send message to server
        await ws.send(b"Hello world")
```

### Environment Detection
The `pyplet/__init__.py` uses import detection to determine runtime environment:
- If `pyplet.server` imports successfully → server environment
- If import fails → client environment (Pyodide)

```python
try:
    from . import server
    is_server, is_client = True, False
except ImportError:
    from . import client
    is_server, is_client = False, True
```

## Development Setup

### Dependencies
- **Build tools**: Cython, pyodide-build
- **Web server**: Tornado (async)
- **Package manager**: uv (recommended) or pip
- **Python version**: ≥3.12

### Installation
```bash
# Clone and setup Pyodide
git clone <repository>
wget https://github.com/pyodide/pyodide/releases/download/0.28.0/pyodide-0.28.0.tar.bz2
tar -xvjf pyodide-0.28.0.tar.bz2

# Install with uv (recommended)
uv venv
uv sync --group examples

# Or with pip
pip install -e .
```

### Running Apps
```bash
# Start server (serves all apps in apps/ directory)
python -m pyplet.server

# Or using CLI
pyplet start
```

### Creating New Apps
```bash
pyplet init my_project_name
```
Creates `apps/my_project_name/` with template files.

## File Locations

### Configuration Files
- `pyproject.toml` - Package metadata and dependencies
- `apps/template/` - Project template for new apps

### Key Source Files
- `pyplet/server/_server.py:1` - Main server implementation
- `pyplet/client/__init__.py:1` - ClientApplication base class
- `pyplet/shared/websocket.py:1` - WebSocket abstraction
- `pyplet/server/cli.py:10` - Project creation logic

## Common Tasks

### Adding Server Dependencies
Edit `pyproject.toml` under `[project].dependencies`

### Adding Example Dependencies
Edit `pyproject.toml` under `[dependency-groups].examples`

### Modifying Server Behavior
Check `pyplet/server/_server.py` for Tornado request handlers

### Modifying Client Behavior
Check `pyplet/client/__init__.py` for ClientApplication class

### DOM Manipulation
Use `pyplet/shared/dom/` modules - available on both client and server for rendering

## Testing

Applications are located in `apps/` directory. The template app demonstrates:
- WebSocket communication
- DOM manipulation via `js` module
- Async/await patterns

## Important Notes for Agents

1. **Dual Runtime**: Code may run in CPython (server) OR Pyodide (browser). Check context carefully.

2. **WebSocket Pattern**: Client-server communication uses async WebSocket abstraction (`pyplet.WebSocket`)

3. **Import Strategy**: The codebase uses try/except import to detect server vs client environment

4. **Pyodide Constraints**: 
   - Client code runs in WebAssembly (limited stdlib)
   - Use `js` module to access browser APIs
   - Not all Python packages are available

5. **File Naming Convention**: 
   - Server files: `{name}_server.py`
   - Client files: `{name}_client.py`
   - Config files: `config.py`

6. **License**: Apache License 2.0

## Useful Commands

```bash
# Install in development mode
pip install -e .

# Sync with examples
uv sync --group examples

# Start server
pyplet start

# Create new project
pyplet init <project_name>

# Run server directly
python -m pyplet.server
```

## Architecture Decisions

- **Why Pyodide?** Enables Python in the browser without server round-trips
- **Why Tornado?** Async web server with excellent WebSocket support
- **Why WebSocket?** Real-time bidirectional communication between Python client/server
- **Why shared modules?** Code reuse between server rendering and client interaction

## Contributing

When modifying this codebase:
1. Maintain separation between client and server modules
2. Use async/await for all I/O operations
3. Keep WebSocket abstraction clean
4. Test in both server and client (browser) contexts
5. Follow existing naming conventions

---

**Repository maintained by**: Maxime Istasse (istassem@gmail.com)

**Last updated**: 2026-01-19
