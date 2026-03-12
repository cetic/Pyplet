from . import shared
from .shared.websocket import WebSocket as Websocket

try:
    from . import server

    is_server, is_client = True, False
except ImportError:
    from . import client

    is_server, is_client = False, True
