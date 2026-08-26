"""pyplet-CORE WebSocket compression tests (qs-port Phase P0).

WHAT THIS PROVES
================
Phase P0 of the QualiSpectra→pyplet port enables Tornado's standard
``permessage-deflate`` extension on the single shared ``ServerWebSocket`` that
fronts EVERY pyplet app, so the chatty JSON/text frames the client exchanges
are compressed on the wire. Two properties are pinned here:

  (a) **``get_compression_options`` opts into compression** — the method
      returns a (non-``None``) dict; returning a dict is exactly how a Tornado
      ``WebSocketHandler`` enables ``permessage-deflate``. We also assert the
      ``compression_level`` we set (6, zlib's default) survives.
  (b) **a real handshake negotiates ``permessage-deflate``** — a client that
      offers the extension (``compression_options={}``) receives a 101 whose
      ``Sec-WebSocket-Extensions`` response header names
      ``permessage-deflate``. Tornado calls ``get_compression_options``
      during the upgrade (before
      ``open``), so a thin no-auth subclass that only neutralizes the auth gate
      still exercises the real, inherited method end-to-end.

The handshake assertion uses Tornado's ``AsyncHTTPTestCase`` harness (shipped
with the existing ``tornado`` dep — no new dependency), mirroring
``tests/healthz_test.py``; the unit assertion builds a bare handler via
``__new__`` like ``tests/prod_hardening_test.py``.
"""

from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application
from tornado.websocket import websocket_connect

from pyplet.server._server import ServerWebSocket


def test_get_compression_options_enables_compression():
    """``get_compression_options`` returns a compression-enabling dict.

    A Tornado ``WebSocketHandler`` opts into ``permessage-deflate`` by
    returning a dict (``None`` disables it); we also pin the
    ``compression_level`` we configured so a silent drop to defaults is caught.
    """
    ws = ServerWebSocket.__new__(ServerWebSocket)
    options = ws.get_compression_options()
    assert isinstance(options, dict), (
        "get_compression_options must return a dict to enable "
        f"permessage-deflate, got {options!r}"
    )
    assert options.get("compression_level") == 6


class _NoAuthWS(ServerWebSocket):
    """``ServerWebSocket`` with the auth gate + origin check neutralized.

    ``get_compression_options`` is inherited unchanged, so the handshake still
    negotiates via the real method; only ``open``/``check_origin`` are stubbed
    so the (routed, argument-less) upgrade completes without a session.
    """

    def check_origin(self, origin):
        return True

    async def open(self):  # noqa: A003 - Tornado handler hook
        pass


class WSCompressionHandshakeTest(AsyncHTTPTestCase):
    """Real-handshake assertion: ``permessage-deflate`` is negotiated."""

    def get_app(self) -> Application:
        return Application([(r"/ws", _NoAuthWS)])

    @gen_test
    async def test_handshake_negotiates_permessage_deflate(self):
        """A client offering the extension gets it back in the 101 response."""
        url = f"ws://127.0.0.1:{self.get_http_port()}/ws"
        conn = await websocket_connect(url, compression_options={})
        try:
            extensions = conn.headers.get("Sec-WebSocket-Extensions", "")
            assert "permessage-deflate" in extensions, (
                "server did not negotiate permessage-deflate; "
                f"Sec-WebSocket-Extensions={extensions!r}"
            )
        finally:
            conn.close()
