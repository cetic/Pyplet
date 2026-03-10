import os

# Generate params dynamically from the module's attributes
params = [
    name
    for name, _ in globals().items()
    if not name.startswith("_") and name != "params"
]

address = os.environ.get("PYPLET_ADDR", "127.0.0.1")
apps = os.environ.get("PYPLET_APPS", "apps")
debug = os.environ.get("PYPLET_DEBUG", "1")
port = int(os.environ.get("PYPLET_PORT", "8080"))
pyodide_url = os.environ.get(
    "PYPLET_PYODIDE",
    "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js",
)
url = os.environ.get("PYPLET_URL", None)
