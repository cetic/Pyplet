"""Cookie-security tests for ``pyplet.server.oauth`` (Story 17.7, PB-9).

Covers DEPLOY-2 (the ``Secure`` attribute on all three auth cookies, gated on
the deployed origin) and SECURI-9 (fail-fast on a missing persistent
``PYPLET_COOKIE_SECRET`` on the production profile).

Mirrors ``tests/config_test.py`` / ``tests/oauth_test.py``: env-driven via the
``monkeypatch`` fixture, no live server. ``_use_secure_cookies`` and
``set_session`` are sync; the two OAuth-state writers (``start_login`` /
``start_drive_consent``) are async and use ``@pytest.mark.asyncio`` (asyncio is
in STRICT mode — pytest-asyncio 1.4.0 is installed).

The Secure decision is gated on ``config.url`` / ``PYPLET_SECURE_COOKIES`` and
**never** on ``handler.request.protocol`` (xheaders is off on the VM behind the
TLS-terminating edge, so ``request.protocol`` is unreliably ``"http"`` even for
https clients — audit DEPLOY-2 verifier note).
"""

import json
from unittest.mock import MagicMock

import pytest

from pyplet.server import oauth

# Env vars that drive the Secure decision and the production startup gate.
_COOKIE_ENV_VARS = (
    "PYPLET_SECURE_COOKIES",
    "PYPLET_URL",
    "PYPLET_COOKIE_SECRET",
    "PYPLET_REQUIRE_AUTH",
    "PYPLET_ALLOW_MAGICLINK",
    "PYPLET_AUTH_RULES_FILE",
    "OAUTH_GOOGLE_CLIENT_ID",
    "OAUTH_GOOGLE_CLIENT_SECRET",
    "OAUTH_MICROSOFT_CLIENT_ID",
    "OAUTH_MICROSOFT_CLIENT_SECRET",
    "MAGICLINK_SMTP_HOST",
    "MAGICLINK_SMTP_USER",
    "MAGICLINK_SMTP_PASSWORD",
)


@pytest.fixture(autouse=True)
def _clear_cookie_env(monkeypatch):
    """Strip every relevant env var so each test starts from a known state."""
    for var in _COOKIE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    yield


def _enable_oauth(monkeypatch):
    """Set Google OAuth env vars so ``auth_enabled()`` is True."""
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "client-secret")


def _write_rules(tmp_path):
    """Write a real (well-formed) auth_rules.json and return its path."""
    rules = tmp_path / "auth_rules.json"
    rules.write_text(json.dumps([[".*", "@example\\.com$"]]))
    return rules


async def _stub_oidc(provider):
    """Async stand-in for ``oauth._fetch_oidc_config`` (no network)."""
    return {
        "authorization_endpoint": (
            "https://accounts.google.com/o/oauth2/v2/auth"
        )
    }


# ---------------------------------------------------------------------------
# AC3(a) — _use_secure_cookies() decision logic
# ---------------------------------------------------------------------------


def test_secure_cookies_true_for_https_url(monkeypatch):
    """https PYPLET_URL (the deployed origin) → Secure on."""
    monkeypatch.setenv("PYPLET_URL", "https://pyplet.example.com")
    assert oauth._use_secure_cookies() is True


def test_secure_cookies_false_for_http_url(monkeypatch):
    """Plain-http PYPLET_URL → Secure off (local dev still sets cookies)."""
    monkeypatch.setenv("PYPLET_URL", "http://127.0.0.1:8080")
    assert oauth._use_secure_cookies() is False


def test_secure_cookies_false_when_url_unset(monkeypatch):
    """Neither flag nor PYPLET_URL set (local dev default) → Secure off."""
    assert oauth._use_secure_cookies() is False


def test_secure_cookies_flag_true_overrides_http_url(monkeypatch):
    """Explicit PYPLET_SECURE_COOKIES=1 wins over a plain-http url."""
    monkeypatch.setenv("PYPLET_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("PYPLET_SECURE_COOKIES", "1")
    assert oauth._use_secure_cookies() is True


def test_secure_cookies_flag_false_overrides_https_url(monkeypatch):
    """Explicit PYPLET_SECURE_COOKIES=0 wins over an https url."""
    monkeypatch.setenv("PYPLET_URL", "https://pyplet.example.com")
    monkeypatch.setenv("PYPLET_SECURE_COOKIES", "0")
    assert oauth._use_secure_cookies() is False


# ---------------------------------------------------------------------------
# AC3(b) — secure= forwarded to set_signed_cookie on all three sites
# ---------------------------------------------------------------------------


def test_set_session_forwards_secure_true_on_https(monkeypatch):
    """The session cookie carries secure=True on an https origin."""
    monkeypatch.setenv("PYPLET_URL", "https://pyplet.example.com")
    handler = MagicMock()
    oauth.set_session(handler, {"sub": "u1", "email": "a@example.com"})
    assert handler.set_signed_cookie.call_args.kwargs.get("secure") is True


def test_set_session_no_secure_on_plain_http(monkeypatch):
    """The session cookie does not carry Secure in plain-http local dev."""
    monkeypatch.setenv("PYPLET_URL", "http://127.0.0.1:8080")
    handler = MagicMock()
    oauth.set_session(handler, {"sub": "u1", "email": "a@example.com"})
    assert not handler.set_signed_cookie.call_args.kwargs.get("secure")


@pytest.mark.asyncio
async def test_start_login_forwards_secure_true_on_https(monkeypatch):
    """The login OAuth-state cookie carries secure=True on an https origin."""
    monkeypatch.setenv("PYPLET_URL", "https://pyplet.example.com")
    _enable_oauth(monkeypatch)
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    handler = MagicMock()
    handler.get_argument.return_value = "/"
    await oauth.start_login(handler, "google")
    assert handler.set_signed_cookie.call_args.kwargs.get("secure") is True


@pytest.mark.asyncio
async def test_start_drive_consent_forwards_secure_true_on_https(monkeypatch):
    """The drive-consent OAuth-state cookie carries secure=True on https."""
    monkeypatch.setenv("PYPLET_URL", "https://pyplet.example.com")
    _enable_oauth(monkeypatch)
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    handler = MagicMock()
    await oauth.start_drive_consent(handler, "/")
    assert handler.set_signed_cookie.call_args.kwargs.get("secure") is True


@pytest.mark.asyncio
async def test_start_login_no_secure_on_plain_http(monkeypatch):
    """The login OAuth-state cookie does not carry Secure in plain-http dev."""
    monkeypatch.setenv("PYPLET_URL", "http://127.0.0.1:8080")
    _enable_oauth(monkeypatch)
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    handler = MagicMock()
    handler.get_argument.return_value = "/"
    await oauth.start_login(handler, "google")
    assert not handler.set_signed_cookie.call_args.kwargs.get("secure")


@pytest.mark.asyncio
async def test_start_drive_consent_no_secure_on_plain_http(monkeypatch):
    """The drive-consent OAuth-state cookie omits Secure in plain-http dev."""
    monkeypatch.setenv("PYPLET_URL", "http://127.0.0.1:8080")
    _enable_oauth(monkeypatch)
    monkeypatch.setattr(oauth, "_fetch_oidc_config", _stub_oidc)
    handler = MagicMock()
    await oauth.start_drive_consent(handler, "/")
    assert not handler.set_signed_cookie.call_args.kwargs.get("secure")


# ---------------------------------------------------------------------------
# AC3(c) — production fail-fast on a missing persistent PYPLET_COOKIE_SECRET
# (SECURI-9): the 4th check inside Story 17.6's enforce_startup_auth_policy().
# ---------------------------------------------------------------------------


def test_enforce_raises_when_production_and_no_cookie_secret(
    monkeypatch, tmp_path
):
    """PYPLET_REQUIRE_AUTH=1 + auth on + unset secret → refuse to boot.

    A real rules file is supplied so 17.6's missing-rules check does not
    mask the cookie-secret check; magic-link is off so its check is skipped.
    """
    _enable_oauth(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(_write_rules(tmp_path)))
    monkeypatch.delenv("PYPLET_COOKIE_SECRET", raising=False)
    assert oauth.auth_enabled() is True
    with pytest.raises(oauth.AuthConfigError):
        oauth.enforce_startup_auth_policy(magiclink_enabled=False)


def test_enforce_allows_when_cookie_secret_set(monkeypatch, tmp_path):
    """Production profile with a persistent secret set → boots."""
    _enable_oauth(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(_write_rules(tmp_path)))
    monkeypatch.setenv("PYPLET_COOKIE_SECRET", "a" * 64)
    result = oauth.enforce_startup_auth_policy(magiclink_enabled=False)
    assert result is None


def test_enforce_allows_when_not_production_without_secret(
    monkeypatch, tmp_path
):
    """Local dev (PYPLET_REQUIRE_AUTH unset) + no secret → boots (no raise)."""
    _enable_oauth(monkeypatch)
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(_write_rules(tmp_path)))
    monkeypatch.delenv("PYPLET_COOKIE_SECRET", raising=False)
    result = oauth.enforce_startup_auth_policy(magiclink_enabled=False)
    assert result is None
