"""Tornado production-hardening tests (Story 18.18).

WHAT THIS PROVES
================
Story 18.18 hardens the single shared Tornado app (``_app_spec`` + the one
``ServerWebSocket``) that fronts EVERY pyplet app behind the edge. Three
pyplet-core changes are pinned here (DEPLOY-8 / SECURI-4):

  (1) **debug asserted OFF in production** — ``enforce_startup_debug_policy``
      refuses to boot when the production profile is active
      (``PYPLET_REQUIRE_AUTH=1``) AND ``PYPLET_DEBUG=1`` (the config default),
      because Tornado debug mode ships autoreload + traceback pages. It is a
      no-op off the production profile, so the everyday (even authenticated)
      local dev loop keeps debug + autoreload. Gating mirrors
      ``oauth.enforce_startup_auth_policy`` (``require_auth``, NOT
      ``auth_enabled()``).
  (2) **``check_origin`` allowlist** — ``ServerWebSocket.check_origin`` allows
      the same-origin case (Tornado default) OR an origin whose host matches
      the deployed ``PYPLET_URL`` host (the edge may rewrite ``Host``); a
      foreign origin is rejected; with ``PYPLET_URL`` unset it falls back to
      the default same-origin check (localhost dev still connects).
  (3) **``xheaders=True`` on listen** — ``astart`` passes ``xheaders=True`` to
      ``app.listen`` so the edge's ``X-Forwarded-For`` / ``X-Forwarded-Proto``
      are trusted (real client IP + https scheme behind the proxy).

These are sync ``def test_*`` functions using ``monkeypatch`` (env-driven
``config``), mirroring ``tests/oauth_test.py``; the xheaders assertion drives
the ``astart`` path with a captured, sentinel-stopped ``Application.listen`` so
the real (blocking) server never starts.
"""

import asyncio
from types import SimpleNamespace

import pytest

from pyplet.server import _server

# ---------------------------------------------------------------------------
# Env hygiene
# ---------------------------------------------------------------------------

_HARDENING_ENV_VARS = ("PYPLET_REQUIRE_AUTH", "PYPLET_DEBUG", "PYPLET_URL")


def _clear_hardening_env(monkeypatch):
    """Remove the env vars that drive the three hardening checks."""
    for var in _HARDENING_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# AC1 — debug asserted OFF in production (enforce_startup_debug_policy)
# ---------------------------------------------------------------------------


def test_debug_policy_raises_when_production_and_debug_on(monkeypatch):
    """Production profile (require_auth=1) + debug=1 → refuse to boot."""
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("PYPLET_DEBUG", "1")
    with pytest.raises(_server.DebugConfigError):
        _server.enforce_startup_debug_policy()


def test_debug_policy_allows_production_with_debug_off(monkeypatch):
    """Production profile + debug=0 → boots (the correct prod combination)."""
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("PYPLET_DEBUG", "0")
    assert _server.enforce_startup_debug_policy() is None


def test_debug_policy_allows_when_not_production_even_with_debug_on(
    monkeypatch,
):
    """require_auth=0 + debug=1 → no raise (local dev keeps autoreload)."""
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "0")
    monkeypatch.setenv("PYPLET_DEBUG", "1")
    assert _server.enforce_startup_debug_policy() is None


def test_debug_policy_allows_when_require_auth_unset_and_debug_on(monkeypatch):
    """require_auth unset (default '0') + debug=1 → no raise.

    The authenticated dev loop (a provider client-id set, but require_auth
    unset) must still boot with debug + autoreload — the gate is
    ``require_auth``, NOT ``auth_enabled()``.
    """
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_DEBUG", "1")
    assert _server.enforce_startup_debug_policy() is None


# ---------------------------------------------------------------------------
# AC3 — check_origin allowlist on ServerWebSocket
# ---------------------------------------------------------------------------


def _make_ws(host_header):
    """Build a bare ``ServerWebSocket`` with only a ``Host`` request header.

    ``check_origin`` (ours + Tornado's default) reads only
    ``self.request.headers['Host']``, so ``__new__`` (skipping the full
    handler/connection init) plus a stub request is sufficient to exercise the
    method logic directly.
    """
    ws = _server.ServerWebSocket.__new__(_server.ServerWebSocket)
    ws.request = SimpleNamespace(headers={"Host": host_header})
    return ws


def test_check_origin_same_origin_allowed_without_allowlist(monkeypatch):
    """No PYPLET_URL → falls back to Tornado's default same-origin check."""
    _clear_hardening_env(monkeypatch)
    ws = _make_ws("localhost:8080")
    assert ws.check_origin("http://localhost:8080") is True


def test_check_origin_foreign_rejected_without_allowlist(monkeypatch):
    """No PYPLET_URL → cross-origin upgrade rejected (same-origin only)."""
    _clear_hardening_env(monkeypatch)
    ws = _make_ws("localhost:8080")
    assert ws.check_origin("http://evil.example.com") is False


def test_check_origin_deployed_origin_allowed_when_host_rewritten(monkeypatch):
    """PYPLET_URL host is allowed even if the edge rewrote the Host header."""
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_URL", "https://deployed.example.com")
    ws = _make_ws("internal-upstream:8080")  # edge rewrote Host
    assert ws.check_origin("https://deployed.example.com") is True


def test_check_origin_foreign_rejected_with_allowlist(monkeypatch):
    """A foreign origin is rejected even with a configured allowlist."""
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_URL", "https://deployed.example.com")
    ws = _make_ws("internal-upstream:8080")
    assert ws.check_origin("https://evil.example.com") is False


def test_check_origin_same_origin_allowed_with_allowlist(monkeypatch):
    """Same-origin still allowed via Tornado's default even when an allowlist
    is configured — the ``super().check_origin`` branch short-circuits before
    the ``PYPLET_URL`` host comparison (AC3 case (a) with the allowlist on).
    The origin matches the Host header but NOT the PYPLET_URL host, so only
    the same-origin branch can grant it."""
    _clear_hardening_env(monkeypatch)
    monkeypatch.setenv("PYPLET_URL", "https://deployed.example.com")
    ws = _make_ws("localhost:8080")
    assert ws.check_origin("http://localhost:8080") is True


# ---------------------------------------------------------------------------
# AC2 — xheaders=True on app.listen (astart path)
# ---------------------------------------------------------------------------


def test_astart_listens_with_xheaders(
    monkeypatch, tmp_path, preserve_config_dict
):
    """``astart`` calls ``app.listen(..., xheaders=True)``.

    The real ``astart`` binds a port then blocks forever on
    ``asyncio.Event().wait()``; here ``Application.listen`` is replaced by a
    capture-and-stop double, the app-module glob targets an empty dir, and
    the two startup policies are neutralized, so the coroutine reaches the
    listen call and exits via the sentinel without standing up a server.

    The ``config.apps`` override is assigned on ``preserve_config_dict``
    and NOT through ``monkeypatch``. Both undos would run, in the order
    ``preserve_config_dict`` then ``monkeypatch`` (teardown is the reverse
    of setup, and the autouse/argument order puts monkeypatch first) — so
    monkeypatch's undo lands *after* the dict restore and re-freezes
    ``apps`` to the value it read, shadowing ``PYPLET_APPS`` for every
    later test in the session. Restoring twice is not idempotent here
    because ``Param.__set__`` writes an override unconditionally.
    """
    captured = {}

    class _StopListen(Exception):
        pass

    def _fake_listen(self, port, address, **kwargs):
        captured["kwargs"] = kwargs
        raise _StopListen

    # Empty apps dir → the server-module glob imports nothing.
    preserve_config_dict.apps = str(tmp_path)
    # No app instances → no route splice into the shared _app_spec.
    monkeypatch.setattr(_server, "server_applications", {})
    # Neutralize both fail-closed startup policies for this listen-path test.
    monkeypatch.setattr(
        _server.oauth, "enforce_startup_auth_policy", lambda **kw: None
    )
    monkeypatch.setattr(_server, "enforce_startup_debug_policy", lambda: None)
    monkeypatch.setattr(
        _server.tornado.web.Application, "listen", _fake_listen
    )

    with pytest.raises(_StopListen):
        asyncio.run(_server.astart())

    assert captured["kwargs"].get("xheaders") is True
