"""Thread the resolved login into ``ServerWebSocket``.

``ServerWebSocket.open`` already resolves the caller's identity via
``_require_auth`` but used to discard it. This pins the one line added there:
right after a successful ``_require_auth`` resolution, ``self.login`` is set
to the resolved user's ``email`` — before the app's ``websocket_server_loop``
is launched — so a consumer app can read
it back via ``getattr(ws, "login", None)``.

Mirrors ``tests/prod_hardening_test.py``'s ``_make_ws`` style: a bare
``ServerWebSocket.__new__`` instance with methods/attributes monkeypatched
directly, no real Tornado request/connection setup. ``open`` calls
``asyncio.create_task(application.websocket_server_loop(self))``, so each
test flushes the newly-created task (diffing ``asyncio.all_tasks()`` before
and after) so it does not leak as an "unawaited task" warning; asyncio is in
STRICT mode (pytest-asyncio 1.4.0), so every async test carries
``@pytest.mark.asyncio``.
"""

import asyncio
from types import SimpleNamespace

import pytest

from pyplet.server import _server


def _make_ws() -> _server.ServerWebSocket:
    """Build a bare ``ServerWebSocket`` with no real Tornado init."""
    return _server.ServerWebSocket.__new__(_server.ServerWebSocket)


async def _flush_new_tasks(before: set) -> None:
    """Await any task ``open()`` scheduled via ``asyncio.create_task``."""
    after = asyncio.all_tasks() - before
    if after:
        await asyncio.gather(*after)


@pytest.mark.asyncio
async def test_open_captures_login_from_resolved_user(monkeypatch):
    """A real resolved user dict lands on ``self.login`` as its ``email``."""
    ws = _make_ws()
    resolved_user = {
        "email": "alice@example.com",
        "name": "Alice",
        "provider": "google",
    }
    monkeypatch.setattr(ws, "_require_auth", lambda *a, **kw: resolved_user)

    async def _noop_loop(_ws):
        return None

    fake_app = SimpleNamespace(websocket_server_loop=_noop_loop)
    monkeypatch.setattr(
        _server, "server_applications", {("proj", "app"): fake_app}
    )

    before = asyncio.all_tasks()
    await ws.open("proj", "app")
    await _flush_new_tasks(before)

    assert ws.login == "alice@example.com"


@pytest.mark.asyncio
async def test_open_captures_anonymous_sentinel_email_verbatim(monkeypatch):
    """The auth-disabled sentinel's empty-string email is threaded as-is.

    Normalizing the empty-string sentinel to a stable anonymous literal is
    an app-side concern — the shared framework must NOT special-case it here,
    it just threads whatever ``_require_auth`` gave it.
    """
    ws = _make_ws()
    anonymous_user = {"email": "", "name": "anonymous", "provider": None}
    monkeypatch.setattr(ws, "_require_auth", lambda *a, **kw: anonymous_user)

    async def _noop_loop(_ws):
        return None

    fake_app = SimpleNamespace(websocket_server_loop=_noop_loop)
    monkeypatch.setattr(
        _server, "server_applications", {("proj", "app"): fake_app}
    )

    before = asyncio.all_tasks()
    await ws.open("proj", "app")
    await _flush_new_tasks(before)

    assert ws.login == ""


@pytest.mark.asyncio
async def test_open_unauthorized_never_sets_login(monkeypatch):
    """When ``_require_auth`` rejects the request, ``self.login`` stays
    unset."""
    ws = _make_ws()
    monkeypatch.setattr(ws, "_require_auth", lambda *a, **kw: None)
    monkeypatch.setattr(ws, "close", lambda *a, **kw: None)

    await ws.open("proj", "app")

    assert getattr(ws, "login", None) is None
