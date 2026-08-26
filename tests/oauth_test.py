"""Fail-closed auth policy tests for ``pyplet.server.oauth`` (Story 17.6,
PB-1).

Covers SECURI-2 / SECURI-1 / SECURI-7: the ``PYPLET_REQUIRE_AUTH`` production
startup assertion (``enforce_startup_auth_policy``), the deny-by-default ACL
when auth is enabled but ``auth_rules.json`` is missing, and the magic-link
refuse-in-production gate (``PYPLET_ALLOW_MAGICLINK`` opt-in).

These are sync ``def test_*`` functions using the ``monkeypatch`` fixture,
mirroring ``tests/config_test.py``. The helper under test is sync, so no
``@pytest.mark.asyncio`` / pytest-asyncio is required.

ACL global-state hygiene: ``oauth._acl_rules`` / ``oauth._acl_allow_all`` are
module globals cached across calls; the autouse fixture resets them before and
after every test so loaded rules never leak between tests.
"""

import json
import logging

import pytest

from pyplet.server import oauth

# Provider / magic-link env vars that drive auth_enabled().
_AUTH_ENV_VARS = (
    "OAUTH_GOOGLE_CLIENT_ID",
    "OAUTH_GOOGLE_CLIENT_SECRET",
    "OAUTH_MICROSOFT_CLIENT_ID",
    "OAUTH_MICROSOFT_CLIENT_SECRET",
    "MAGICLINK_SMTP_HOST",
    "MAGICLINK_SMTP_USER",
    "MAGICLINK_SMTP_PASSWORD",
)

# Production-profile policy flags introduced by Story 17.6.
_POLICY_ENV_VARS = ("PYPLET_REQUIRE_AUTH", "PYPLET_ALLOW_MAGICLINK")


@pytest.fixture(autouse=True)
def _reset_acl_state():
    """Reset oauth's cached ACL module globals before and after each test."""
    oauth._acl_rules = None
    oauth._acl_allow_all = False
    yield
    oauth._acl_rules = None
    oauth._acl_allow_all = False


def _clear_auth_env(monkeypatch):
    """Remove every provider / magic-link / policy env var (raising=False)."""
    for var in _AUTH_ENV_VARS + _POLICY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _write_rules(tmp_path):
    """Write a real (well-formed) auth_rules.json and return its path."""
    rules = tmp_path / "auth_rules.json"
    rules.write_text(json.dumps([[".*", "@example\\.com$"]]))
    return rules


# ---------------------------------------------------------------------------
# AC4(a) — PYPLET_REQUIRE_AUTH production startup assertion (SECURI-2)
# ---------------------------------------------------------------------------


def test_enforce_raises_when_production_and_no_auth_method(monkeypatch):
    """Production profile + no auth method configured → refuse to boot."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    assert oauth.auth_enabled() is False
    with pytest.raises(oauth.AuthConfigError):
        oauth.enforce_startup_auth_policy(magiclink_enabled=False)


def test_enforce_warns_when_auth_off_and_not_production(monkeypatch, caplog):
    """Auth off and not production → returns None (warns, does not raise)."""
    _clear_auth_env(monkeypatch)
    with caplog.at_level(logging.WARNING, logger="pyplet.server.oauth"):
        result = oauth.enforce_startup_auth_policy(magiclink_enabled=False)
    assert result is None
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)


# ---------------------------------------------------------------------------
# AC4(b) — deny-by-default ACL when auth on and rules file missing (SECURI-1)
# ---------------------------------------------------------------------------


def test_acl_denies_by_default_when_auth_on_and_no_rules_file(
    monkeypatch, tmp_path
):
    """Auth enabled but no rules file → is_app_permitted denies (fail
    closed)."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "y")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(tmp_path / "nope.json"))
    oauth.reload_acl()
    assert oauth.is_app_permitted("any", "app", "user@example.com") is False


def test_acl_allows_all_when_auth_disabled_and_no_rules_file(
    monkeypatch, tmp_path
):
    """Auth fully disabled (local dev) preserves allow-all on a missing
    file."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(tmp_path / "nope.json"))
    oauth.reload_acl()
    assert oauth.is_app_permitted("any", "app", "user@example.com") is True


# ---------------------------------------------------------------------------
# AC4(c) — production + auth on + rules file missing → refuse to boot
# ---------------------------------------------------------------------------


def test_enforce_raises_when_production_auth_on_and_no_rules_file(
    monkeypatch, tmp_path
):
    """Production profile + auth on + missing rules file → refuse to boot."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "y")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(tmp_path / "nope.json"))
    with pytest.raises(oauth.AuthConfigError):
        oauth.enforce_startup_auth_policy(magiclink_enabled=False)


# ---------------------------------------------------------------------------
# AC4(d) — magic-link refuse-in-production unless PYPLET_ALLOW_MAGICLINK
# (SECURI-7)
# ---------------------------------------------------------------------------


def test_enforce_raises_when_production_magiclink_without_optin(
    monkeypatch, tmp_path
):
    """Production profile + magic-link on + no opt-in → refuse to boot."""
    _clear_auth_env(monkeypatch)
    rules = _write_rules(tmp_path)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "y")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(rules))
    with pytest.raises(oauth.AuthConfigError):
        oauth.enforce_startup_auth_policy(magiclink_enabled=True)


def test_enforce_allows_magiclink_with_explicit_optin(monkeypatch, tmp_path):
    """Production profile + magic-link on + PYPLET_ALLOW_MAGICLINK=1 →
    boots."""
    _clear_auth_env(monkeypatch)
    rules = _write_rules(tmp_path)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("PYPLET_ALLOW_MAGICLINK", "1")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "y")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(rules))
    # Story 17.7 (PB-9): a fully-configured production profile also requires a
    # persistent PYPLET_COOKIE_SECRET, else the 4th check refuses to boot.
    monkeypatch.setenv("PYPLET_COOKIE_SECRET", "x" * 64)
    result = oauth.enforce_startup_auth_policy(magiclink_enabled=True)
    assert result is None


# ---------------------------------------------------------------------------
# Production happy path — regression guard for a real deployment
# (PYPLET_REQUIRE_AUTH=1 + OAuth configured + rules file present + no
# magic-link). The fail-closed helper must NOT take down a correctly-configured
# production server (the story's latent-safe guarantee, AC1/AC5).
# ---------------------------------------------------------------------------


def test_enforce_allows_fully_configured_production_profile(
    monkeypatch, tmp_path
):
    """Production profile fully configured (OAuth + rules file, no magic-link)
    → boots (does not raise)."""
    _clear_auth_env(monkeypatch)
    rules = _write_rules(tmp_path)
    monkeypatch.setenv("PYPLET_REQUIRE_AUTH", "1")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "y")
    monkeypatch.setenv("PYPLET_AUTH_RULES_FILE", str(rules))
    # Story 17.7 (PB-9): a fully-configured production profile also requires a
    # persistent PYPLET_COOKIE_SECRET, else the 4th check refuses to boot.
    monkeypatch.setenv("PYPLET_COOKIE_SECRET", "x" * 64)
    result = oauth.enforce_startup_auth_policy(magiclink_enabled=False)
    assert result is None
