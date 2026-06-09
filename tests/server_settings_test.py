"""WebSocket frame-size setting (Story 18.17 — SCALIN-4).

pyplet-core previously set no ``websocket_max_message_size`` on its Tornado
``Application``, so the WS handler kept Tornado's ~10 MB default and a base64'd
document upload exceeded the frame and killed the socket before app code ran.
Story 18.17 adds the setting to ``_app_spec`` from the new
``PYPLET_WS_MAX_MESSAGE_MB`` knob (default 40 MB).

The env override is covered at the ``Param`` level in ``config_test.py``.
``_app_spec`` is frozen at module-import time, so this test pins only the
concrete default on the frozen spec (a computed comparison against
``config.ws_max_message_mb`` would be flaky under a prior env monkeypatch).
"""

from pyplet.server._server import _app_spec


def test_app_spec_sets_websocket_max_message_size():
    """``_app_spec`` carries ``websocket_max_message_size`` (40 MB default).

    Asserts the concrete default (``40 * 1024 * 1024``), NOT
    ``config.ws_max_message_mb * 1024 * 1024``: ``_app_spec`` is built once at
    import while the ``Param`` re-reads the env at access time, so the computed
    comparison would be flaky if a prior test monkeypatched the env var.
    """
    assert "websocket_max_message_size" in _app_spec
    assert _app_spec["websocket_max_message_size"] == 40 * 1024 * 1024
