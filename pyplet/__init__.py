from . import shared  # noqa: F401
from .shared.websocket import WebSocket  # noqa: F401

try:
    from . import server  # noqa: F401

    is_server, is_client = True, False

except ImportError:
    from . import client  # noqa: F401

    is_server, is_client = False, True
