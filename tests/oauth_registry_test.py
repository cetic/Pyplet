"""Registry tests for ``pyplet.server.oauth`` — providers and consent flows.

``oauth`` is the provider-agnostic OIDC engine: it branches on no provider name
and hardcodes no vendor endpoint. What used to be a hardcoded provider dict and
a hardcoded Drive-consent path is now two open registries, filled through
:func:`oauth.register_provider` and :func:`oauth.register_consent_flow`.

These tests pin that genericity from the outside — every one of them registers
a **fictional** provider/flow, never a shipped preset, so a test passing here
proves the engine really does work for a provider it has never heard of. The
observable behaviour previously covered only for Google/Drive is covered here
against that fictional provider: the authorize URL, the state cookie's
``flow`` field, the callback routing to the flow instead of the session, and
the "a failing flow must not strand the browser" guarantee.

No network: ``_fetch_oidc_config`` and the token-exchange ``httpx`` client are
stubbed. Async tests use ``@pytest.mark.asyncio`` (STRICT mode).
"""

import json
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

from pyplet.server import oauth

_AUTH_ENDPOINT = "https://id.example.test/authorize"
_TOKEN_ENDPOINT = "https://id.example.test/token"

# A provider the framework has never heard of, declared entirely by a test.
_SPEC = {
    "label": "Example ID",
    "openid_config_url": (
        "https://id.example.test/.well-known/openid-configuration"
    ),
    "client_id": "example-client",
    "client_secret": "example-secret",
    "scopes": ["openid", "email"],
}


@pytest.fixture(autouse=True)
def _isolate_registries(monkeypatch):
    """Give each test its own copy of both registries.

    ``register_provider``/``register_consent_flow`` mutate module-level dicts,
    so without this a test that registers or overrides would leak into the
    next one (and into the rest of the session).
    """
    monkeypatch.setattr(
        oauth, "_PROVIDER_CONFIGS", dict(oauth._PROVIDER_CONFIGS)
    )
    monkeypatch.setattr(oauth, "_CONSENT_FLOWS", dict(oauth._CONSENT_FLOWS))
    yield


def _handler(**arguments):
    """A Tornado-handler double whose ``get_argument`` serves *arguments*."""
    handler = MagicMock()
    handler.get_argument.side_effect = lambda name, default=None: (
        arguments.get(name, default)
    )
    return handler


def _redirect_params(handler):
    """Parse the query of the URL the handler was redirected to."""
    url = handler.redirect.call_args.args[0]
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def _state_cookie(handler):
    """Decode the JSON written into the signed OAuth-state cookie."""
    return json.loads(handler.set_signed_cookie.call_args.args[1])


async def _stub_oidc(provider):
    """Async stand-in for ``oauth._fetch_oidc_config`` (no network)."""
    return {
        "authorization_endpoint": _AUTH_ENDPOINT,
        "token_endpoint": _TOKEN_ENDPOINT,
        "issuer": "https://id.example.test",
    }


# ---------------------------------------------------------------------------
# register_provider
# ---------------------------------------------------------------------------


def test_register_provider_makes_it_enabled_and_labelled():
    """A registered provider with a client_id shows up as an enabled one."""
    oauth.register_provider("example", _SPEC)
    assert "example" in oauth.enabled_providers()
    assert oauth.provider_label("example") == "Example ID"


def test_register_provider_without_client_id_is_not_enabled():
    """A registered-but-unconfigured provider offers no login button.

    Same contract the shipped presets rely on: registration is not
    configuration, an empty client_id keeps it off the login page.
    """
    oauth.register_provider("example", {**_SPEC, "client_id": ""})
    assert "example" not in oauth.enabled_providers()


def test_provider_label_falls_back_to_the_name():
    """A spec without a label still renders sensibly on the login page."""
    spec = {k: v for k, v in _SPEC.items() if k != "label"}
    oauth.register_provider("example", spec)
    assert oauth.provider_label("example") == "Example"


@pytest.mark.parametrize(
    "missing", ["openid_config_url", "client_id", "client_secret"]
)
def test_register_provider_rejects_an_incomplete_spec(missing):
    """A spec missing a required key fails at registration, not at login."""
    spec = {k: v for k, v in _SPEC.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        oauth.register_provider("example", spec)
    assert "example" not in oauth._PROVIDER_CONFIGS


def test_register_provider_overrides_a_previous_registration():
    """Re-registering a name replaces it — how an app overrides a preset."""
    oauth.register_provider("example", _SPEC)
    oauth.register_provider("example", {**_SPEC, "label": "Corporate SSO"})
    assert oauth.provider_label("example") == "Corporate SSO"
    assert len([n for n in oauth._PROVIDER_CONFIGS if n == "example"]) == 1


def test_spec_values_may_be_callables_resolved_at_use_time():
    """A callable spec value is resolved per use, not frozen at registration.

    This is what lets a spec read config/env lazily: the client_id below only
    becomes non-empty after registration, and the provider becomes enabled
    without re-registering.
    """
    box = {"client_id": ""}
    oauth.register_provider(
        "example", {**_SPEC, "client_id": lambda: box["client_id"]}
    )
    assert "example" not in oauth.enabled_providers()
    box["client_id"] = "configured-later"
    assert "example" in oauth.enabled_providers()


@pytest.mark.asyncio
async def test_start_login_uses_the_registered_spec(monkeypatch):
    """The authorize URL comes wholly from the spec — no vendor default."""
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    oauth.register_provider(
        "example", {**_SPEC, "auth_params": {"prompt": "login"}}
    )
    handler = _handler(next="/somewhere")

    await oauth.start_login(handler, "example")

    params = _redirect_params(handler)
    assert handler.redirect.call_args.args[0].startswith(_AUTH_ENDPOINT)
    assert params["client_id"] == "example-client"
    assert params["scope"] == "openid email"
    assert params["prompt"] == "login"  # spec auth_params beat the default
    assert _state_cookie(handler)["next"] == "/somewhere"


@pytest.mark.asyncio
async def test_start_login_on_an_unregistered_provider_raises(monkeypatch):
    """An unregistered name fails loudly, naming what IS registered."""
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    with pytest.raises(KeyError, match="nope"):
        await oauth.start_login(_handler(), "nope")


# ---------------------------------------------------------------------------
# register_consent_flow / start_consent
# ---------------------------------------------------------------------------


async def _noop_complete(handler, user_info, tokens):
    """Consent completion that records nothing."""
    return None


def _register_flow(**overrides):
    """Register the fictional provider plus a consent flow against it."""
    oauth.register_provider("example", _SPEC)
    flow = {
        "provider": "example",
        "scopes": ["https://api.example.test/auth/files"],
        "auth_params": {"access_type": "offline", "prompt": "consent"},
        "on_complete": _noop_complete,
    }
    flow.update(overrides)
    oauth.register_consent_flow("files", flow)
    return flow


@pytest.mark.parametrize("missing", ["provider", "on_complete"])
def test_register_consent_flow_rejects_an_incomplete_spec(missing):
    """A flow missing a required key fails at registration."""
    flow = {"provider": "example", "on_complete": _noop_complete}
    del flow[missing]
    with pytest.raises(ValueError, match=missing):
        oauth.register_consent_flow("files", flow)
    assert "files" not in oauth._CONSENT_FLOWS


@pytest.mark.asyncio
async def test_start_consent_adds_flow_scopes_and_params(monkeypatch):
    """Consent asks the provider's scopes PLUS the flow's, with its params."""
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    _register_flow()
    handler = _handler()

    await oauth.start_consent(handler, "files", "/back-here")

    params = _redirect_params(handler)
    assert params["scope"] == (
        "openid email https://api.example.test/auth/files"
    )
    assert params["access_type"] == "offline"
    assert params["prompt"] == "consent"  # flow params beat the provider's
    assert params["client_id"] == "example-client"  # same client as login


@pytest.mark.asyncio
async def test_start_consent_marks_the_flow_in_the_state_cookie(monkeypatch):
    """The state cookie carries the flow name — what routes the callback."""
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    _register_flow()
    handler = _handler()

    await oauth.start_consent(handler, "files", "/back-here")

    cookie = _state_cookie(handler)
    assert cookie["flow"] == "files"
    assert cookie["provider"] == "example"
    assert cookie["next"] == "/back-here"


@pytest.mark.asyncio
async def test_start_consent_on_an_unregistered_flow_raises(monkeypatch):
    """An unregistered flow fails loudly rather than redirecting nowhere."""
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    with pytest.raises(KeyError, match="nope"):
        await oauth.start_consent(_handler(), "nope", "/")


# ---------------------------------------------------------------------------
# handle_callback — consent routing
# ---------------------------------------------------------------------------


def _stub_callback(monkeypatch, tokens=None):
    """Stub discovery, the token exchange and id_token verification."""
    tokens = tokens or {
        "id_token": "opaque",
        "refresh_token": "refresh-abc",
        "scope": "openid email https://api.example.test/auth/files",
    }
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)

    async def _verify(id_token, provider):
        return {"sub": "u-1", "email": "User@Example.test", "name": "User"}

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
            return _Resp()

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _Client)
    return tokens


def _callback_handler(flow="files"):
    """A handler mid-callback: matching state cookie, code in the query."""
    state = {"state": "s-1", "next": "/back-here", "provider": "example"}
    if flow:
        state["flow"] = flow
    handler = _handler(state="s-1", code="the-code")
    handler.get_signed_cookie.return_value = json.dumps(state)
    return handler


@pytest.mark.asyncio
async def test_callback_hands_the_tokens_to_the_flow(monkeypatch):
    """A consent callback reaches on_complete with the raw token response."""
    tokens = _stub_callback(monkeypatch)
    seen = {}

    async def _complete(handler, user_info, tok):
        seen["user_info"] = user_info
        seen["tokens"] = tok

    _register_flow(on_complete=_complete)
    handler = _callback_handler()

    await oauth.handle_callback(handler)

    assert seen["tokens"] == tokens  # incl. refresh_token + granted scope
    assert seen["user_info"]["sub"] == "u-1"
    assert seen["user_info"]["email"] == "user@example.test"  # normalised
    handler.redirect.assert_called_once_with("/back-here")


@pytest.mark.asyncio
async def test_callback_does_not_touch_the_session_on_a_consent_flow(
    monkeypatch,
):
    """Incremental consent must not re-issue the login session cookie."""
    _stub_callback(monkeypatch)
    sessions = []
    monkeypatch.setattr(
        oauth, "set_session", lambda h, info: sessions.append(info)
    )
    _register_flow()

    await oauth.handle_callback(_callback_handler())

    assert sessions == []


@pytest.mark.asyncio
async def test_callback_without_a_flow_still_logs_in(monkeypatch):
    """The plain login callback is untouched by the consent routing."""
    _stub_callback(monkeypatch)
    sessions = []
    monkeypatch.setattr(
        oauth, "set_session", lambda h, info: sessions.append(info)
    )
    oauth.register_provider("example", _SPEC)

    handler = _callback_handler(flow=None)
    await oauth.handle_callback(handler)

    assert [info["email"] for info in sessions] == ["user@example.test"]
    handler.redirect.assert_called_once_with("/back-here")


@pytest.mark.asyncio
async def test_a_failing_flow_still_redirects_the_browser(monkeypatch):
    """A raising on_complete is logged and swallowed, never a dead end.

    The browser is mid-redirect from the provider; a bookkeeping failure in
    the app must not strand it on an error page.
    """
    _stub_callback(monkeypatch)

    async def _boom(handler, user_info, tokens):
        raise RuntimeError("could not store the token")

    _register_flow(on_complete=_boom)
    handler = _callback_handler()

    await oauth.handle_callback(handler)

    handler.redirect.assert_called_once_with("/back-here")


@pytest.mark.asyncio
async def test_callback_for_an_unregistered_flow_is_refused(monkeypatch):
    """A state cookie naming an unknown flow is a 400, never a silent login.

    Without this the engine would fall through to set_session and turn a
    consent round-trip into an unrequested login.
    """
    _stub_callback(monkeypatch)
    sessions = []
    monkeypatch.setattr(
        oauth, "set_session", lambda h, info: sessions.append(info)
    )
    oauth.register_provider("example", _SPEC)

    handler = _callback_handler(flow="never-registered")
    await oauth.handle_callback(handler)

    handler.set_status.assert_called_once_with(400)
    assert sessions == []
    handler.redirect.assert_not_called()
