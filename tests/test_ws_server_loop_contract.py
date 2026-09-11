"""A ``ServerApplication`` with no ``websocket_server_loop`` still serves."""

import asyncio
import inspect

from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application
from tornado.websocket import websocket_connect

from pyplet.server._server import (
    ServerApplication,
    ServerWebSocket,
    server_applications,
)

_PROJECT = "loop_contract_project"
_APP = "loop_contract_app"


class _NoLoopApp(ServerApplication):
    """An application declaring no ``websocket_server_loop`` override."""


class _CapturingWS(ServerWebSocket):
    """``ServerWebSocket`` recording instances; only ``initialize`` added."""

    instances: list["_CapturingWS"] = []

    def initialize(self):
        super().initialize()
        type(self).instances.append(self)


def test_base_loop_is_awaitable_like_its_client_twin():
    """The base hook returns an awaitable, as ``ClientApplication``'s does."""
    assert inspect.iscoroutinefunction(ServerApplication.websocket_server_loop), (
        "ServerApplication.websocket_server_loop must be a coroutine "
        "function: ServerWebSocket.open passes its result straight to "
        "asyncio.create_task, which raises TypeError on the None a "
        "synchronous stub returns"
    )
    pending = ServerApplication().websocket_server_loop(None)
    assert inspect.isawaitable(pending), (
        f"calling the base hook must yield an awaitable, got {pending!r}"
    )
    pending.close()


class NoServerLoopSocketTest(AsyncHTTPTestCase):
    """A loop-less app connects, carries traffic and closes cleanly."""

    def setUp(self):
        self._saved_apps = dict(server_applications)
        server_applications[(_PROJECT, _APP)] = _NoLoopApp()
        _CapturingWS.instances.clear()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        server_applications.clear()
        server_applications.update(self._saved_apps)
        _CapturingWS.instances.clear()

    def get_app(self) -> Application:
        return Application(
            [
                (r"/apps/([^/]+)/([^/]+)\.ws", ServerWebSocket),
                (r"/probe/([^/]+)/([^/]+)\.ws", _CapturingWS),
            ]
        )

    @gen_test
    async def test_open_logs_no_error_and_leaves_the_socket_alive(self):
        """No ``tornado.application`` ERROR, and the socket is not closed."""
        url = f"ws://127.0.0.1:{self.get_http_port()}/apps/{_PROJECT}/{_APP}.ws"
        with self.assertNoLogs("tornado.application", level="ERROR"):
            conn = await websocket_connect(url)
            try:
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(conn.read_message(), 0.25)
                assert conn.close_code is None, (
                    "the server closed a socket its application still uses "
                    f"for other traffic (close_code={conn.close_code})"
                )
            finally:
                conn.close()

    @gen_test
    async def test_message_and_close_still_reach_the_handler_queue(self):
        """``on_message``/``on_close`` work with no loop draining the queue."""
        url = f"ws://127.0.0.1:{self.get_http_port()}/probe/{_PROJECT}/{_APP}.ws"
        conn = await websocket_connect(url)
        await conn.write_message("ping")

        assert _CapturingWS.instances, "no handler instance was created"
        handler = _CapturingWS.instances[-1]

        queued = await asyncio.wait_for(handler.queue.get(), 2)
        assert queued == "ping", (
            f"on_message must enqueue client traffic, got {queued!r}"
        )

        conn.close()
        closed = await asyncio.wait_for(handler.queue.get(), 2)
        assert closed == ServerWebSocket.closing_message, (
            "on_close must enqueue the closing sentinel even when no "
            f"server loop ever consumed the queue, got {closed!r}"
        )
