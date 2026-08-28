"""
pyplet.server.oauth_providers
=============================

The OIDC provider **presets** Pyplet ships out of the box.

``pyplet.server.oauth`` is the provider-agnostic engine: discovery, the CSRF
state cookie, the code exchange, JWKS signature verification, the signed
session cookie and the fail-closed startup policy. It names no provider — it
holds an open registry instead, and this module is the catalog that pre-fills
it at import so an env-only deployment (set ``OAUTH_GOOGLE_CLIENT_ID`` +
``OAUTH_GOOGLE_CLIENT_SECRET``, get a "Continue with Google" button) keeps
working with zero application code.

The split is the point: the engine has no branch on a provider name, so
**adding a provider is data, not a code change**. Add a preset here to ship one
with the framework, or call ``oauth.register_provider()`` from an application
at import time to add — or override — one without touching the framework at
all. Registering under an existing name replaces that preset.

Every spec value may be a zero-argument callable: the engine resolves it at
use time, so a preset reads ``config`` (hence the environment) lazily, when
the flow runs, instead of freezing it at import time.
"""

from __future__ import annotations

from typing import Any

from .config import config

_GOOGLE_OPENID_CONFIG_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
_MICROSOFT_OPENID_CONFIG_URL = (
    "https://login.microsoftonline.com/"
    "{tenant}/v2.0/.well-known/openid-configuration"
)

BUILTIN_PROVIDERS: dict[str, dict[str, Any]] = {
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
