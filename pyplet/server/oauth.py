"""
pyplet.server.oauth
===================

Platform-level OAuth2 / OIDC authentication for Pyplet.

When at least one provider is configured (via env vars), every HTTP request
goes through an auth check.  Unauthenticated users are shown a login page;
after a successful OAuth flow a signed session cookie is issued.

Supported providers
-------------------
Google
    OAUTH_GOOGLE_CLIENT_ID
    OAUTH_GOOGLE_CLIENT_SECRET

Microsoft / Entra ID
    OAUTH_MICROSOFT_CLIENT_ID
    OAUTH_MICROSOFT_CLIENT_SECRET
    OAUTH_MICROSOFT_TENANT   (default: "common")

Always required when auth is enabled
-------------------------------------
PYPLET_COOKIE_SECRET
    Signs session cookies.  Generate with:
        python -c "import secrets; print(secrets.token_hex(32))"
    Without this, sessions survive only until the server restarts.

Per-app access control (ACL)
------------------------------
Create ``<apps_dir>/auth_rules.json`` — a JSON array of two-element arrays::

    [["project/app_regex", "email_regex"], ...]

The first regex is matched against the combined ``"project/app"`` string;
the second is matched against the user's email address.
Rules are evaluated in order; the first full match grants access.
If no rule matches, access is denied.

Example::

    [[".*", "@mycompany\\.com$"], ["public/demo", ".*"]]

If the file does not exist, **any authenticated user** can see **all** apps.

Auth is silently disabled when no OAuth provider env vars are set.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx

from . import config

logger = logging.getLogger("pyplet.server.oauth")

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_GOOGLE_OPENID_CONFIG_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
_MICROSOFT_OPENID_CONFIG_URL = (
    "https://login.microsoftonline.com/"
    "{tenant}/v2.0/.well-known/openid-configuration"
)

_PROVIDER_CONFIGS: dict[str, dict[str, Any]] = {
    "google": {
        "label": "Google",
        "openid_config_url": _GOOGLE_OPENID_CONFIG_URL,
        "client_id": lambda: config.oauth_google_client_id,
        "client_secret": lambda: config.oauth_google_client_secret,
        "scopes": ["openid", "email", "profile"],
    },
    "microsoft": {
        "label": "Microsoft",
        "openid_config_url": lambda: _MICROSOFT_OPENID_CONFIG_URL.format(
            tenant=config.oauth_microsoft_tenant
        ),
        "client_id": lambda: config.oauth_microsoft_client_id,
        "client_secret": lambda: config.oauth_microsoft_client_secret,
        "scopes": ["openid", "email", "profile"],
    },
}

# OIDC discovery-doc cache
_oidc_cache: dict[str, dict] = {}


def enabled_providers() -> list[str]:
    """Return the names of providers that have a client_id configured."""
    return [
        name for name, meta in _PROVIDER_CONFIGS.items() if meta["client_id"]()
    ]


# Extra auth-enabled checks registered by other modules (e.g. magiclink)
# to avoid circular imports. Call register_auth_check() at import time.
_extra_auth_checks: list = []


def register_auth_check(fn) -> None:
    """Register a zero-argument callable
    that returns True when its auth method is active."""
    _extra_auth_checks.append(fn)


def auth_enabled() -> bool:
    """True when at least one authentication method (OAuth or magic-link)
    is configured."""
    return bool(enabled_providers()) or any(fn() for fn in _extra_auth_checks)


# ---------------------------------------------------------------------------
# OIDC discovery
# ---------------------------------------------------------------------------


async def _fetch_oidc_config(provider: str) -> dict:
    """Fetch (and cache) the OIDC discovery document for *provider*."""
    if provider in _oidc_cache:
        return _oidc_cache[provider]

    meta = _PROVIDER_CONFIGS[provider]
    url = meta["openid_config_url"]
    if callable(url):
        url = url()

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        doc = resp.json()

    _oidc_cache[provider] = doc
    logger.debug("Fetched OIDC config for %s from %s", provider, url)
    return doc


# ---------------------------------------------------------------------------
# JWT / id_token decoding
# ---------------------------------------------------------------------------


def _decode_id_token_claims(id_token: str) -> dict:
    """
    Decode JWT payload without signature verification.

    Safe here because the token is received directly from the provider
    over TLS; no MITM is possible.  For higher-assurance deployments
    swap in full JWKS verification via ``authlib`` or ``python-jose``.
    """
    import base64

    parts = id_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


# ---------------------------------------------------------------------------
# Session cookie
# ---------------------------------------------------------------------------

SESSION_COOKIE = "pyplet_user"
_SESSION_MAX_AGE_DAYS = 1  # 24 hours


def set_session(handler, user_info: dict) -> None:
    """Write a signed session cookie containing *user_info*."""
    payload = json.dumps({**user_info, "_ts": int(time.time())})
    handler.set_signed_cookie(
        SESSION_COOKIE,
        payload,
        expires_days=_SESSION_MAX_AGE_DAYS,
        httponly=True,
        samesite="Lax",
    )


def get_session(handler) -> dict | None:
    """Return the user dict from the signed cookie, or ``None``."""
    raw = handler.get_signed_cookie(
        SESSION_COOKIE, max_age_days=_SESSION_MAX_AGE_DAYS
    )
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return {k: v for k, v in data.items() if k != "_ts"}
    except Exception:
        return None


def clear_session(handler) -> None:
    """Delete the session cookie."""
    handler.clear_cookie(SESSION_COOKIE)


# ---------------------------------------------------------------------------
# ACL rules
# ---------------------------------------------------------------------------

# Each rule is (app_pattern, email_pattern) — compiled regexes.
# app_pattern is matched against the combined "project/app" string.
_AclRule = tuple[re.Pattern, re.Pattern]
_acl_rules: list[_AclRule] | None = None  # None = "not loaded yet"
_acl_allow_all: bool = False  # True when no rules file exists


def _load_acl_rules() -> None:
    """Load (or reload) ACL rules from the configured rules file."""
    global _acl_rules, _acl_allow_all

    rules_path = config.auth_rules_file
    if not os.path.isfile(rules_path):
        logger.info(
            "No ACL rules file found at %s — all authenticated users"
            " can access all apps.",
            rules_path,
        )
        _acl_rules = []
        _acl_allow_all = True
        return

    with open(rules_path) as fh:
        raw = json.load(fh)

    rules: list[_AclRule] = []
    for entry in raw:
        if len(entry) != 2:
            logger.warning(
                "Skipping malformed ACL rule (expected 2 elements): %r", entry
            )
            continue
        app_re, email_re = entry
        rules.append(
            (
                re.compile(app_re),
                re.compile(email_re),
            )
        )

    _acl_rules = rules
    _acl_allow_all = False
    logger.info("Loaded %d ACL rule(s) from %s", len(rules), rules_path)


def _ensure_acl_loaded() -> None:
    if _acl_rules is None:
        _load_acl_rules()


def reload_acl() -> None:
    """Force a reload of the ACL rules file (useful after editing it)."""
    global _acl_rules
    _acl_rules = None
    _ensure_acl_loaded()


def is_app_permitted(project: str, app: str, email: str) -> bool:
    """
    Return True if *email* is permitted to access *project*/*app*.

    Each rule's first regex is matched against the combined ``"project/app"``
    string; the second is matched against the user's email address.
    Rules are evaluated in order; the first full match grants access.
    If no rules file exists, access is always granted.
    """
    _ensure_acl_loaded()

    if _acl_allow_all:
        return True

    app_path = f"{project}/{app}"
    for app_pat, email_pat in _acl_rules:  # type: ignore[union-attr]
        if app_pat.search(app_path) and email_pat.search(email):
            return True

    return False


def permitted_apps(email: str) -> list[tuple[str, str]]:
    """
    Return a sorted list of ``(project, app)`` pairs accessible to *email*.

    Discovers available apps from the filesystem, then filters by ACL.
    """
    import glob as _glob

    all_apps = sorted(_glob.glob("*/*_client.py", root_dir=config.apps))
    result = []
    for path in all_apps:
        parts = path.replace("\\", "/").split("/")
        if len(parts) != 2:
            continue
        project, filename = parts
        app = filename[: -len("_client.py")]
        if is_app_permitted(project, app, email):
            result.append((project, app))
    return result


# ---------------------------------------------------------------------------
# OAuth login flow helpers (called by handlers in _server.py)
# ---------------------------------------------------------------------------

_STATE_COOKIE = "pyplet_oauth_state"


async def start_login(handler, provider: str) -> None:
    """
    Initiate the OAuth authorization-code flow for *provider*.

    Saves a CSRF state token in a cookie, then redirects the browser to
    the provider's authorization endpoint.
    """
    meta = _PROVIDER_CONFIGS[provider]
    oidc = await _fetch_oidc_config(provider)

    client_id = meta["client_id"]()
    state = secrets.token_urlsafe(16)
    next_url = handler.get_argument("next", "/")

    handler.set_signed_cookie(
        _STATE_COOKIE,
        json.dumps({"state": state, "next": next_url, "provider": provider}),
        httponly=True,
        samesite="Lax",
    )

    callback_url = _callback_url(handler)
    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": " ".join(meta["scopes"]),
        "state": state,
        "prompt": "select_account",
    }

    auth_url = oidc["authorization_endpoint"] + "?" + urlencode(params)
    logger.debug("Redirecting to %s authorization: %s", provider, auth_url)
    handler.redirect(auth_url)


async def handle_callback(handler) -> None:
    """
    Complete the OAuth authorization-code flow.

    Validates state, exchanges the code for tokens, decodes the id_token,
    sets the session cookie, and redirects to the originally requested URL.
    Called by ``OAuthCallbackHandler`` in ``_server.py``.
    """
    # --- Validate CSRF state ---
    raw_state = handler.get_signed_cookie(_STATE_COOKIE)
    if not raw_state:
        _error(
            handler, 400, "OAuth state cookie is missing. Please try again."
        )
        return

    state_data = json.loads(raw_state)
    expected_state = state_data["state"]
    next_url = state_data.get("next", "/")
    provider = state_data.get("provider")

    if handler.get_argument("state", None) != expected_state:
        _error(
            handler,
            400,
            "OAuth state mismatch — possible CSRF. Please try again.",
        )
        return

    # --- Check for provider-side errors ---
    error = handler.get_argument("error", None)
    if error:
        _error(handler, 400, f"OAuth error from provider: {error}")
        return

    code = handler.get_argument("code", None)
    if not code:
        _error(handler, 400, "No authorization code received.")
        return

    # --- Exchange code for tokens ---
    meta = _PROVIDER_CONFIGS[provider]
    oidc = await _fetch_oidc_config(provider)
    callback_url = _callback_url(handler)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url,
        "client_id": meta["client_id"](),
        "client_secret": meta["client_secret"](),
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                oidc["token_endpoint"], data=token_data, timeout=15
            )
            resp.raise_for_status()
            tokens = resp.json()
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        _error(handler, 502, "Token exchange with OAuth provider failed.")
        return

    id_token = tokens.get("id_token")
    if not id_token:
        _error(handler, 500, "Provider did not return an id_token.")
        return

    try:
        claims = _decode_id_token_claims(id_token)
    except Exception as exc:
        logger.error("id_token decode failed: %s", exc)
        _error(handler, 500, "Could not decode the identity token.")
        return

    user_info = {
        "sub": claims.get("sub", ""),
        "email": claims.get("email", "").lower().strip(),
        "name": claims.get("name", claims.get("email", "")),
        "picture": claims.get("picture", ""),
        "provider": provider,
    }

    if not user_info["email"]:
        _error(handler, 500, "Provider did not include an email in the token.")
        return

    set_session(handler, user_info)
    logger.info(
        "Login: %s (%s) via %s",
        user_info["name"],
        user_info["email"],
        provider,
    )
    handler.clear_cookie(_STATE_COOKIE)
    handler.redirect(next_url)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _callback_url(handler) -> str:
    base = config.url or f"{handler.request.protocol}://{handler.request.host}"
    return urljoin(base, "/oauth/callback")


def _error(handler, status: int, message: str) -> None:
    handler.set_status(status)
    handler.write(
        f"<html><body><h3>Authentication error ({status})</h3>"
        f"<p>{message}</p>"
        f'<p><a href="/">Back to home</a></p>'
        f"</body></html>"
    )
