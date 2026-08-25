"""
pyplet.server.oauth
===================

Platform-level OAuth2 / OIDC authentication for Pyplet.

When at least one provider is configured (via env vars), every HTTP request
goes through an auth check.  Unauthenticated users are shown a login page;
after a successful OAuth flow a signed session cookie is issued.

Providers
---------
This module is the provider-agnostic OIDC **engine**: it branches on no
provider name and hardcodes no vendor endpoint. Providers live in an open
registry, filled by :func:`register_provider`; the presets Pyplet ships (and
the env vars that configure them) live in :mod:`pyplet.server.oauth_providers`
and are registered at the bottom of this module. An application adds — or
overrides — a provider by calling :func:`register_provider` at import time.

Incremental consent
-------------------
A flow registered with :func:`register_consent_flow` and started with
:func:`start_consent` re-runs the authorization-code round-trip on top of an
existing login to obtain **extra scopes** (and, when it asks for offline
access, a refresh token) without touching the session. The engine routes the
callback back to the flow by the ``"flow"`` field of the state cookie, so what
those scopes are for is entirely the application's business.

Always required when auth is enabled
-------------------------------------
PYPLET_COOKIE_SECRET
    Signs session cookies.  Generate with:
        python -c "import secrets; print(secrets.token_hex(32))"
    Without this, a random secret is generated per process, so sessions
    survive only until the server restarts; under PYPLET_REQUIRE_AUTH=1
    the server refuses to boot if unset.

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

Deny-by-default (Story 17.6, PB-1): when auth is **enabled** but the rules
file is missing, ACL **denies** all app access (fail closed) and logs an
ERROR. When auth is fully disabled (no provider — local dev), a missing file
still allows all apps so an un-authenticated local run works.

Fail-closed startup (``PYPLET_REQUIRE_AUTH=1``): on this production profile
``enforce_startup_auth_policy()`` refuses to boot when no auth method is
configured, when ``auth_rules.json`` is missing, or when magic-link is enabled
without ``PYPLET_ALLOW_MAGICLINK=1``. Without the flag, auth is silently
disabled when no OAuth provider env vars are set (a loud WARNING is logged).
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx

from .config import config
from .oauth_providers import BUILTIN_PROVIDERS

logger = logging.getLogger("pyplet.server.oauth")

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

# Registered OIDC providers, keyed by name. Deliberately EMPTY here: the engine
# below ships no provider of its own and never branches on a provider name.
# Pyplet's own presets are registered at the bottom of this module, from the
# ``oauth_providers`` catalog, through the same public entry point an
# application uses.
_PROVIDER_CONFIGS: dict[str, dict[str, Any]] = {}

# Spec keys without which a login cannot even be attempted. Checked at
# registration so a malformed spec fails at import — where the traceback names
# the offending app — instead of at the first login attempt in production.
_REQUIRED_PROVIDER_KEYS = ("openid_config_url", "client_id", "client_secret")

# Applied when a spec omits them. ``select_account`` is plain OIDC (it stops a
# provider silently re-using its own ambient session), not vendor knowledge.
_DEFAULT_SCOPES = ("openid", "email", "profile")
_DEFAULT_AUTH_PARAMS = {"prompt": "select_account"}


def register_provider(name: str, spec: Mapping[str, Any]) -> None:
    """Register the OIDC provider *name*, replacing any spec already there.

    Args:
        name: Registry key. Also the ``?provider=`` value accepted by
            ``/oauth/login`` and the ``"provider"`` field recorded in the
            session cookie.
        spec: The provider description. Required keys:

            ``openid_config_url``
                URL of the OIDC discovery document.
            ``client_id`` / ``client_secret``
                The OAuth2 client credentials.

            Optional keys:

            ``label``
                Human-readable name for the login button (default:
                ``name.title()``).
            ``scopes``
                Scopes requested at login (default: openid/email/profile).
            ``auth_params``
                Extra authorization-endpoint query params, replacing the
                engine default ``{"prompt": "select_account"}``.

            Any value may be a zero-argument callable, which the engine
            resolves at use time — that is how a spec reads ``config`` (hence
            the environment) lazily rather than freezing it at import.

    Raises:
        ValueError: When a required key is missing.
    """
    missing = [key for key in _REQUIRED_PROVIDER_KEYS if key not in spec]
    if missing:
        raise ValueError(
            f"OAuth provider {name!r} is missing required spec key(s): "
            f"{', '.join(missing)}"
        )
    if name in _PROVIDER_CONFIGS:
        logger.debug("Replacing the registered OAuth provider %r", name)
    _PROVIDER_CONFIGS[name] = dict(spec)


def _provider(name: str) -> dict[str, Any]:
    """Return the spec registered under *name*.

    Raises:
        KeyError: When nothing is registered under that name — with the
            registered names in the message, since an unknown provider is
            almost always a missing ``register_provider()`` call at boot.
    """
    try:
        return _PROVIDER_CONFIGS[name]
    except KeyError:
        raise KeyError(
            f"No OAuth provider registered under {name!r} "
            f"(registered: {sorted(_PROVIDER_CONFIGS) or 'none'})"
        ) from None


def _spec_value(spec: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Read *key* from a provider/flow spec, calling it when it is callable."""
    value = spec.get(key, default)
    return value() if callable(value) else value


# OIDC discovery-doc cache
_oidc_cache: dict[str, dict] = {}

# JWKS cache, keyed by provider (parallel to ``_oidc_cache``). Providers rotate
# their signing keys (major ones roughly daily), so a verify failure that
# looks like rotation triggers a single forced refetch — see
# ``_verify_id_token_claims``.
_jwks_cache: dict[str, dict] = {}


def enabled_providers() -> list[str]:
    """Return the names of providers that have a client_id configured."""
    return [
        name
        for name, meta in _PROVIDER_CONFIGS.items()
        if _spec_value(meta, "client_id")
    ]


def provider_label(name: str) -> str:
    """Human-readable name for *name*, for the login button.

    Falls back to a title-cased name, so a provider registered by an app
    renders sensibly without declaring a label.
    """
    spec = _PROVIDER_CONFIGS.get(name, {})
    return _spec_value(spec, "label") or name.title()


# Extra auth-enabled checks registered by other modules (e.g. magiclink)
# to avoid circular imports. Call register_auth_check() at import time.
_extra_auth_checks: list = []


def register_auth_check(fn) -> None:
    """Register a zero-argument callable
    that returns True when its auth method is active."""
    _extra_auth_checks.append(fn)


# Incremental-consent flows registered by a server application, keyed by name.
# A flow re-runs the authorization-code round-trip on top of an existing login
# to obtain extra scopes without touching the session; ``handle_callback``
# routes the response to the flow's completion callback — instead of
# ``set_session`` — keyed by the ``"flow"`` field of the state cookie.
_CONSENT_FLOWS: dict[str, dict[str, Any]] = {}

_REQUIRED_FLOW_KEYS = ("provider", "on_complete")


def register_consent_flow(name: str, flow: Mapping[str, Any]) -> None:
    """Register the incremental-consent flow *name*, replacing any existing.

    Args:
        name: Flow key — stored in the state cookie's ``"flow"`` field and
            passed to :func:`start_consent`.
        flow: The flow description. Required keys:

            ``provider``
                Name of a registered provider to run the flow against.
            ``on_complete``
                ``async (handler, user_info, tokens) -> None``, awaited once
                the callback has verified the id_token. It receives the raw
                token response, so a flow that asked for offline access reads
                its own ``refresh_token``/``scope`` out of it — the engine
                does not interpret those. Exceptions are logged and swallowed:
                a failing flow must not strand the browser mid-redirect.

            Optional keys:

            ``scopes``
                Extra scopes, appended to the provider's login scopes.
            ``auth_params``
                Extra authorization-endpoint params, merged over the
                provider's (e.g. whatever the provider wants in order to
                return a refresh token).

            As for a provider spec, any value may be a zero-argument callable.

    Raises:
        ValueError: When a required key is missing.
    """
    missing = [key for key in _REQUIRED_FLOW_KEYS if key not in flow]
    if missing:
        raise ValueError(
            f"OAuth consent flow {name!r} is missing required spec key(s): "
            f"{', '.join(missing)}"
        )
    if name in _CONSENT_FLOWS:
        logger.debug("Replacing the registered consent flow %r", name)
    _CONSENT_FLOWS[name] = dict(flow)


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

    url = _spec_value(_provider(provider), "openid_config_url")

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        doc = resp.json()

    _oidc_cache[provider] = doc
    logger.debug("Fetched OIDC config for %s from %s", provider, url)
    return doc


async def _fetch_jwks(provider: str, *, force_refresh: bool = False) -> dict:
    """Fetch (and cache) *provider*'s JWKS — its JSON Web Key Set.

    Reads ``jwks_uri`` from the already-cached OIDC discovery document and
    GETs it with the same ``httpx`` pattern as :func:`_fetch_oidc_config`.
    The result is cached per provider; ``force_refresh=True`` bypasses the
    cache to pick up a rotated signing key.
    """
    if not force_refresh and provider in _jwks_cache:
        return _jwks_cache[provider]

    oidc = await _fetch_oidc_config(provider)
    jwks_uri = oidc["jwks_uri"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri, timeout=10)
        resp.raise_for_status()
        jwks = resp.json()

    _jwks_cache[provider] = jwks
    logger.debug("Fetched JWKS for %s from %s", provider, jwks_uri)
    return jwks


# ---------------------------------------------------------------------------
# id_token signature verification (SECURI-8, Story 18.19)
# ---------------------------------------------------------------------------


def _accepted_issuers(issuer: str) -> list[str]:
    """Return the set of acceptable ``iss`` values for *issuer*.

    Some providers issue ``iss`` as the bare host while their discovery
    document advertises the ``https://`` form, so accept both spellings of the
    discovered issuer. For a provider whose ``iss`` matches its discovery
    ``issuer`` exactly this is effectively a singleton.
    """
    out = [issuer]
    if issuer.startswith("https://"):
        out.append(issuer.removeprefix("https://"))
    return out


def _verify_id_token_against_jwks(
    id_token: str, jwks: dict, *, issuer: str, audience: str
) -> dict:
    """Verify the ``id_token`` signature against *jwks*; validate its claims.

    Pure and synchronous (no ``httpx``, no ``config``) so the crypto is
    unit-testable with crafted JWTs and a stubbed JWKS — no async, no network.
    Restricts the accepted signing algorithm to RS256 (the algorithm every
    provider Pyplet ships a preset for signs with) to close
    algorithm-confusion, resolves the signing key from *jwks* by ``kid``, and
    validates ``iss``/``aud``/``exp``.

    Args:
        id_token: The compact-serialized JWT from the token endpoint.
        jwks: The provider JWKS (``{"keys": [...]}`` from ``jwks_uri``).
        issuer: The discovery ``issuer`` — the expected ``iss`` (the bare-host
            variant is also accepted, see :func:`_accepted_issuers`).
        audience: The provider ``client_id`` — the expected ``aud``.

    Returns:
        The validated claims as a plain ``dict``.

    Raises:
        JoseError: On a bad/absent signature, a wrong/missing ``iss``/``aud``,
            an expired/absent ``exp``, or a non-RS256 algorithm.
        ValueError: When no JWKS key matches the token's ``kid`` (rotation).
    """
    from authlib.jose import JsonWebKey, JsonWebToken

    key_set = JsonWebKey.import_key_set(jwks)
    claims = JsonWebToken(["RS256"]).decode(
        id_token,
        key_set,
        claims_options={
            "iss": {"essential": True, "values": _accepted_issuers(issuer)},
            "aud": {"essential": True, "value": audience},
            "exp": {"essential": True},
        },
    )
    claims.validate()
    return dict(claims)


async def _verify_id_token_claims(id_token: str, provider: str) -> dict:
    """Verify *id_token* against *provider*'s JWKS and return its claims.

    Async wrapper around the pure :func:`_verify_id_token_against_jwks`:
    resolves the expected ``issuer`` (discovery ``issuer``) and ``audience``
    (the provider ``client_id``), fetches the JWKS, and verifies. On a
    signature/key-resolution failure that looks like key rotation (a
    ``BadSignatureError`` or an unknown-``kid`` ``ValueError``) it refetches
    the JWKS **once** and retries — providers rotate their signing keys, so a
    freshly rotated key may post-date the cache. Claim failures (wrong or
    expired ``iss``/``aud``/``exp``) are NOT retried (the key already
    resolved; a refetch cannot help) and propagate immediately.

    Raises:
        Exception: Any verification failure. ``handle_callback``'s ``try``
            wraps it into the standard error page — no session is set.
    """
    from authlib.jose.errors import BadSignatureError

    oidc = await _fetch_oidc_config(provider)
    issuer = oidc["issuer"]
    audience = _spec_value(_provider(provider), "client_id")

    jwks = await _fetch_jwks(provider)
    try:
        return _verify_id_token_against_jwks(
            id_token, jwks, issuer=issuer, audience=audience
        )
    except (BadSignatureError, ValueError):
        # Signature/key-resolution miss — refetch once in case the signing key
        # rotated past our cache, then retry. A genuinely bad signature fails
        # again on the fresh keys and propagates.
        jwks = await _fetch_jwks(provider, force_refresh=True)
        return _verify_id_token_against_jwks(
            id_token, jwks, issuer=issuer, audience=audience
        )


# ---------------------------------------------------------------------------
# Session cookie
# ---------------------------------------------------------------------------

SESSION_COOKIE = "pyplet_user"


def _use_secure_cookies() -> bool:
    """Whether auth cookies must carry the ``Secure`` attribute.

    Behind a TLS-terminating edge the VM receives plain http with xheaders
    OFF, so ``handler.request.protocol`` is unreliably ``"http"`` even for an
    https client (audit DEPLOY-2). Decide from config, never request.protocol:
    an explicit ``PYPLET_SECURE_COOKIES`` wins; otherwise derive from the https
    scheme of ``config.url``. Plain-http local dev (flag unset, no https url)
    → False, so dev still sets cookies over http.
    """
    flag = config.secure_cookies
    if flag is not None and str(flag).strip() != "":
        return str(flag).strip().lower() in ("1", "true", "yes", "on")
    return (config.url or "").lower().startswith("https://")


def set_session(handler, user_info: dict) -> None:
    """Write a signed session cookie containing *user_info*."""
    payload = json.dumps({**user_info, "_ts": int(time.time())})
    handler.set_signed_cookie(
        SESSION_COOKIE,
        payload,
        expires_days=config.session_max_age_days,
        httponly=True,
        samesite="Lax",
        secure=_use_secure_cookies(),
    )


def get_session(handler) -> dict | None:
    """Return the user dict from the signed cookie, or ``None``."""
    raw = handler.get_signed_cookie(
        SESSION_COOKIE, max_age_days=config.session_max_age_days
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
_acl_allow_all: bool = False  # True only when no rules file AND auth disabled


def _load_acl_rules() -> None:
    """Load (or reload) ACL rules from the configured rules file."""
    global _acl_rules, _acl_allow_all

    rules_path = config.auth_rules_file
    if not os.path.isfile(rules_path):
        if auth_enabled():
            # Fail CLOSED: auth is on but no rules file → deny all by default.
            logger.error(
                "No ACL rules file at %s while auth is enabled — denying all "
                "app access by default (deny-by-default). Ship "
                "auth_rules.json.",
                rules_path,
            )
            _acl_rules = []
            _acl_allow_all = False
            return
        # Auth fully disabled (local dev, no provider) — allow all so an
        # un-authenticated local run still works.
        logger.info(
            "No ACL rules file at %s and auth disabled — allowing all apps "
            "(local dev).",
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
    When auth is enabled but no rules file exists, access is denied
    (deny-by-default, Story 17.6); the allow-all-on-missing-file path
    survives only when auth is fully disabled (local dev).
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
# Fail-closed startup policy (Story 17.6, PB-1)
# ---------------------------------------------------------------------------


class AuthConfigError(RuntimeError):
    """Raised at startup when a fail-closed auth policy is violated.

    Refusing to boot is intentional: a misdelivered auth config must
    hard-fail rather than silently serve every app anonymously (PB-1).
    """


def enforce_startup_auth_policy(magiclink_enabled: bool = False) -> None:
    """Fail-closed startup checks for the production profile (PB-1,
    Story 17.6).

    On the production profile (``PYPLET_REQUIRE_AUTH=1``) raises
    ``AuthConfigError`` — refusing to boot — when (1) no auth method is
    configured, (2) auth is enabled but ``auth_rules.json`` is missing, or
    (3) magic-link is configured without ``PYPLET_ALLOW_MAGICLINK=1``. Off the
    production profile it logs a loud WARNING/ERROR instead of raising, so an
    explicitly-open local dev run still starts.

    Args:
        magiclink_enabled: whether magic-link auth is active. Passed in by the
            caller (``_server.astart`` → ``magiclink.enabled()``) to avoid an
            ``oauth``↔``magiclink`` circular import.

    Side effects: emits log records; reads ``config`` + env.
    Raises: ``AuthConfigError`` to abort startup on a production-profile
        breach.
    """
    production = config.require_auth == "1"

    if not auth_enabled():
        if production:
            raise AuthConfigError(
                "PYPLET_REQUIRE_AUTH=1 but no authentication method is "
                "configured — refusing to boot (would serve every app "
                "anonymously). Configure an OAuth provider (see "
                "pyplet.server.oauth_providers for the shipped presets and "
                "their env vars) or magic-link, or unset PYPLET_REQUIRE_AUTH "
                "for an explicitly open deployment."
            )
        logger.warning(
            "Authentication is DISABLED (no provider configured) — every "
            "request is served anonymously. Set PYPLET_REQUIRE_AUTH=1 with a "
            "configured provider on any non-local deployment."
        )
        return

    if not os.path.isfile(config.auth_rules_file):
        msg = (
            "auth_rules.json not found at %s while authentication is enabled "
            "— ACL DENIES all app access by default (fail closed)."
            % config.auth_rules_file
        )
        if production:
            raise AuthConfigError(
                msg + " Refusing to boot under PYPLET_REQUIRE_AUTH; ship "
                "auth_rules.json in the deploy artifact."
            )
        logger.error(msg)

    if production and magiclink_enabled and config.allow_magiclink != "1":
        raise AuthConfigError(
            "Magic-link (MAGICLINK_SMTP_*) is configured on the production "
            "profile (PYPLET_REQUIRE_AUTH=1) — refusing to boot. Magic-link "
            "mints a session for ANY email and bypasses the OAuth/ACL "
            "boundary. Set PYPLET_ALLOW_MAGICLINK=1 to opt in explicitly."
        )

    # Story 17.7 (PB-9 / SECURI-9): a persistent signing secret is mandatory in
    # production — without it _server.py:325 falls back to a per-process
    # secrets.token_hex(32) that invalidates every session on each restart.
    if production and not config.oauth_cookie_secret:
        raise AuthConfigError(
            "PYPLET_REQUIRE_AUTH=1 but PYPLET_COOKIE_SECRET is unset — "
            "refusing to boot with a per-process random cookie secret "
            "(it would log out every user on each restart). "
            "Set a persistent PYPLET_COOKIE_SECRET "
            '(python -c "import secrets; print(secrets.token_hex(32))").'
        )


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
    meta = _provider(provider)
    oidc = await _fetch_oidc_config(provider)

    client_id = _spec_value(meta, "client_id")
    state = secrets.token_urlsafe(16)
    next_url = handler.get_argument("next", "/")

    handler.set_signed_cookie(
        _STATE_COOKIE,
        json.dumps({"state": state, "next": next_url, "provider": provider}),
        httponly=True,
        samesite="Lax",
        secure=_use_secure_cookies(),
    )

    callback_url = _callback_url(handler)
    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": " ".join(_provider_scopes(meta)),
        "state": state,
        **_provider_auth_params(meta),
    }

    auth_url = oidc["authorization_endpoint"] + "?" + urlencode(params)
    logger.debug("Redirecting to %s authorization: %s", provider, auth_url)
    handler.redirect(auth_url)


async def start_consent(handler, name: str, next_url: str = "/") -> None:
    """Initiate the registered incremental-consent flow *name*.

    Re-runs the authorization-code flow against the flow's provider, using the
    same OAuth client as login, asking for the provider's login scopes PLUS the
    flow's extra scopes. Stores ``"flow": name`` in the state cookie so
    :func:`handle_callback` hands the tokens to the flow's ``on_complete``
    instead of calling :func:`set_session`.

    Does not modify the login session (the user stays logged in throughout).

    Args:
        handler: Tornado RequestHandler.
        name: A flow registered with :func:`register_consent_flow`.
        next_url: URL to redirect to once consent completes.

    Returns:
        None (redirects the browser).

    Raises:
        KeyError: When no such flow (or its provider) is registered.
    """
    flow = _consent_flow(name)
    provider = flow["provider"]
    meta = _provider(provider)
    oidc = await _fetch_oidc_config(provider)
    client_id = _spec_value(meta, "client_id")
    state = secrets.token_urlsafe(16)

    handler.set_signed_cookie(
        _STATE_COOKIE,
        json.dumps(
            {
                "state": state,
                "next": next_url,
                "provider": provider,
                "flow": name,
            }
        ),
        httponly=True,
        samesite="Lax",
        secure=_use_secure_cookies(),
    )

    callback_url = _callback_url(handler)
    scopes = _provider_scopes(meta) + list(
        _spec_value(flow, "scopes", ()) or ()
    )
    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        **_provider_auth_params(meta),
        **(_spec_value(flow, "auth_params", {}) or {}),
    }
    auth_url = oidc["authorization_endpoint"] + "?" + urlencode(params)
    logger.debug("Redirecting to %s consent flow %r", provider, name)
    handler.redirect(auth_url)


async def handle_callback(handler) -> None:
    """
    Complete the OAuth authorization-code flow.

    Validates state, exchanges the code for tokens, verifies the id_token
    signature against the provider JWKS, sets the session cookie, and redirects
    to the originally requested URL. Called by ``OAuthCallbackHandler`` in
    ``_server.py``.
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
    meta = _provider(provider)
    oidc = await _fetch_oidc_config(provider)
    callback_url = _callback_url(handler)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url,
        "client_id": _spec_value(meta, "client_id"),
        "client_secret": _spec_value(meta, "client_secret"),
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
        claims = await _verify_id_token_claims(id_token, provider)
    except Exception as exc:
        logger.error("id_token verification failed: %s", exc)
        _error(handler, 500, "Could not verify the identity token.")
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

    # Incremental-consent callback — do NOT call set_session (the user is
    # already logged in). Hand the raw token response to the flow that started
    # this round-trip, then redirect back to the app. A flow that raises is
    # logged and swallowed: the browser is mid-redirect and must not be
    # stranded on an error page by a bookkeeping failure.
    flow_name = state_data.get("flow")
    if flow_name:
        flow = _CONSENT_FLOWS.get(flow_name)
        if flow is None:
            _error(
                handler,
                400,
                f"Unknown consent flow: {flow_name!r}. Please try again.",
            )
            return
        try:
            await flow["on_complete"](handler, user_info, tokens)
        except Exception as exc:
            logger.error("Consent flow %r failed: %s", flow_name, exc)
        handler.clear_cookie(_STATE_COOKIE)
        handler.redirect(next_url)
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


def _consent_flow(name: str) -> dict[str, Any]:
    """Return the consent flow registered under *name*.

    Raises:
        KeyError: When nothing is registered under that name.
    """
    try:
        return _CONSENT_FLOWS[name]
    except KeyError:
        raise KeyError(
            f"No OAuth consent flow registered under {name!r} "
            f"(registered: {sorted(_CONSENT_FLOWS) or 'none'})"
        ) from None


def _provider_scopes(meta: Mapping[str, Any]) -> list[str]:
    """Login scopes for a provider spec, defaulting to plain OIDC."""
    return list(_spec_value(meta, "scopes") or _DEFAULT_SCOPES)


def _provider_auth_params(meta: Mapping[str, Any]) -> dict[str, str]:
    """Extra authorization-endpoint params for a provider spec."""
    return dict(_spec_value(meta, "auth_params") or _DEFAULT_AUTH_PARAMS)


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


# ---------------------------------------------------------------------------
# Built-in providers
# ---------------------------------------------------------------------------
# Registered at import, generically, from the shipped catalog — nothing above
# names a provider. An env-only deployment therefore keeps its login page with
# no application code, while an app is free to override any of these (or add
# its own) by calling register_provider() at its own import time, which runs
# later: apps are loaded before the Tornado app is built.


def _register_builtin_providers() -> None:
    """Fill the registry from :mod:`pyplet.server.oauth_providers`."""
    for name, spec in BUILTIN_PROVIDERS.items():
        register_provider(name, spec)


_register_builtin_providers()
