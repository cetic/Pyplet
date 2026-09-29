"""Refusal paths of ``oauth.handle_callback`` — an error page, no session.
Discovery, the token exchange and id_token verification are stubbed.
"""

import json
from unittest.mock import MagicMock

import pytest

from pyplet.server import oauth

_MISSING = object()

_SPEC = {
    "label": "Example ID",
    "openid_config_url": ("https://id.example.test/.well-known/openid-configuration"),
    "client_id": "example-client",
    "client_secret": "example-secret",
    "scopes": ["openid", "email"],
}


async def _stub_oidc(provider):
    """Async stand-in for ``oauth._fetch_oidc_config`` (no network)."""
    return {
        "authorization_endpoint": "https://id.example.test/authorize",
        "token_endpoint": "https://id.example.test/token",
    }


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Own copy of both registries, the fictional provider, no network."""
    monkeypatch.setattr(oauth, "_PROVIDER_CONFIGS", dict(oauth._PROVIDER_CONFIGS))
    monkeypatch.setattr(oauth, "_CONSENT_FLOWS", dict(oauth._CONSENT_FLOWS))
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    oauth.register_provider("example", _SPEC)


@pytest.fixture
def sessions(monkeypatch):
    """Collect every session ``handle_callback`` would open."""
    opened = []
    monkeypatch.setattr(oauth, "set_session", lambda h, info: opened.append(info))
    return opened


def _handler(state="s-1", code="the-code", cookie=_MISSING, **arguments):
    """A handler mid-callback; *cookie* replaces the signed state cookie."""
    arguments.setdefault("state", state)
    arguments.setdefault("code", code)
    handler = MagicMock()
    handler.get_argument.side_effect = lambda name, default=None: arguments.get(
        name, default
    )
    if cookie is _MISSING:
        cookie = json.dumps(
            {"state": "s-1", "next": "/back-here", "provider": "example"}
        )
    handler.get_signed_cookie.return_value = cookie
    return handler


def _stub_tokens(monkeypatch, tokens, claims=None, post=None):
    """Stub the exchange with *tokens*, the verification with *claims*."""

    async def _verify(id_token, provider):
        if claims is None:
            raise ValueError("unverifiable id_token")
        return claims

    monkeypatch.setattr(oauth, "_verify_id_token_claims", _verify)

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return tokens

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, timeout=None):
            if post is not None:
                return post()
            return _Resp()

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _Client)


def _assert_refused(handler, status, sessions):
    """The handler answered *status*, opened no session, went nowhere."""
    handler.set_status.assert_called_once_with(status)
    assert sessions == []
    handler.redirect.assert_not_called()


@pytest.mark.asyncio
async def test_callback_refuses_a_missing_state_cookie(sessions):
    """No state cookie: the round-trip cannot be authenticated."""
    handler = _handler(cookie=None)
    await oauth.handle_callback(handler)
    _assert_refused(handler, 400, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_a_state_mismatch(sessions):
    """A query state that misses the cookie is a possible CSRF."""
    handler = _handler(state="forged")
    await oauth.handle_callback(handler)
    _assert_refused(handler, 400, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_a_provider_side_error(sessions):
    """``?error=`` from the provider is reported, never ignored."""
    handler = _handler(error="access_denied")
    await oauth.handle_callback(handler)
    _assert_refused(handler, 400, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_a_missing_code(sessions):
    """No authorization code means nothing to exchange."""
    handler = _handler(code=None)
    await oauth.handle_callback(handler)
    _assert_refused(handler, 400, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_a_failed_exchange(monkeypatch, sessions):
    """A provider that refuses the exchange is a 502, not a login."""

    def _boom():
        raise RuntimeError("token endpoint down")

    _stub_tokens(monkeypatch, {}, claims={}, post=_boom)
    handler = _handler()
    await oauth.handle_callback(handler)
    _assert_refused(handler, 502, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_a_response_without_an_id_token(monkeypatch, sessions):
    """A token response with no id_token identifies nobody."""
    _stub_tokens(monkeypatch, {"access_token": "a-1"}, claims={})
    handler = _handler()
    await oauth.handle_callback(handler)
    _assert_refused(handler, 500, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_an_unverifiable_id_token(monkeypatch, sessions):
    """A failing signature or claims check is never a trusted login."""
    _stub_tokens(monkeypatch, {"id_token": "opaque"}, claims=None)
    handler = _handler()
    await oauth.handle_callback(handler)
    _assert_refused(handler, 500, sessions)


@pytest.mark.asyncio
async def test_callback_refuses_claims_without_an_email(monkeypatch, sessions):
    """The session identity is the email; without one the callback fails."""
    _stub_tokens(
        monkeypatch,
        {"id_token": "opaque"},
        claims={"sub": "u-1", "name": "User"},
    )
    handler = _handler()
    await oauth.handle_callback(handler)
    _assert_refused(handler, 500, sessions)
