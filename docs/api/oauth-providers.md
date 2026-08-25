# OAuth providers and consent flows

`pyplet.server.oauth` is a provider-agnostic OIDC engine. It owns discovery,
the CSRF state cookie, the code exchange, JWKS signature verification, the
signed session cookie and the fail-closed startup policy — and it branches on
no provider name and hardcodes no vendor endpoint.

Everything vendor-specific lives in one of two places:

- **`pyplet.server.oauth_providers`** — the presets Pyplet ships (Google,
  Microsoft/Entra ID), registered into the engine at import.
- **Your application** — anything else, registered from your own module at
  import time.

## Registering a provider

```python
from pyplet.server import oauth

oauth.register_provider("corporate", {
    "label": "Corporate SSO",                       # login-button text
    "openid_config_url": "https://id.corp.example/.well-known/openid-configuration",
    "client_id": lambda: os.environ.get("CORP_CLIENT_ID", ""),
    "client_secret": lambda: os.environ.get("CORP_CLIENT_SECRET", ""),
    "scopes": ["openid", "email", "profile"],
    "auth_params": {"prompt": "select_account"},    # optional
})
```

`openid_config_url`, `client_id` and `client_secret` are required; a spec
missing one raises `ValueError` **at registration**, so the traceback names the
app instead of surfacing as a broken login in production.

Any value may be a zero-argument callable, resolved at use time. That is how a
spec reads configuration lazily rather than freezing an env var at import.

A provider only appears on the login page once its `client_id` resolves to
something non-empty — registration is not configuration. Registering an
existing name **replaces** it, which is how an app overrides a shipped preset
(apps are loaded before the Tornado app is built, so an app-side registration
always wins).

## Incremental consent

An incremental-consent flow re-runs the authorization-code round-trip on top of
an existing login to obtain **extra scopes** — and, if it asks for offline
access, a refresh token — without touching the session. The user stays logged
in throughout.

```python
async def _store_token(handler, user_info, tokens):
    """Called once the callback has verified the id_token."""
    await save_refresh_token(
        user_info["sub"], tokens.get("refresh_token"), tokens.get("scope", "")
    )

oauth.register_consent_flow("files", {
    "provider": "corporate",
    "scopes": ["https://api.corp.example/auth/files"],
    "auth_params": {"access_type": "offline", "prompt": "consent"},
    "on_complete": _store_token,
})
```

Start it from a Tornado handler:

```python
await oauth.start_consent(handler, "files", next_url="/apps/me/back-here")
```

`start_consent` stores `"flow": "files"` in the state cookie; `handle_callback`
reads it back and hands the **raw token response** to `on_complete` instead of
calling `set_session`. The engine does not interpret `refresh_token` or
`scope` — what the extra scopes are for is entirely the application's business.

Two deliberate behaviours:

- An exception from `on_complete` is logged and swallowed, then the browser is
  redirected anyway. It is mid-redirect from the provider; a bookkeeping
  failure must not strand it on an error page.
- A state cookie naming an **unregistered** flow is refused with a 400. Falling
  through would turn a consent round-trip into an unrequested login.

## Migrating off the Drive-specific API

The engine previously carried a Google-Drive-shaped path: `register_drive_token_hook()`,
`start_drive_consent()`, and a `state["flow"] == "drive"` branch in the
callback, with `drive.file`/`access_type=offline` hardcoded. That was one
application's requirement living in the framework. It is replaced by the
generic pair above.

| Removed | Replacement |
| --- | --- |
| `register_drive_token_hook(fn)` | `register_consent_flow(name, {...,"on_complete": fn})` |
| `start_drive_consent(handler, next_url)` | `start_consent(handler, name, next_url)` |
| hardcoded `state["flow"] == "drive"` | any registered flow name |
| hardcoded `drive.file` scope + `access_type=offline` | the flow's `scopes` / `auth_params` |

The hook signature changes from `(sub, email, refresh_token, scopes)` to
`(handler, user_info, tokens)`. Adapt an existing hook in place:

```python
oauth.register_consent_flow("drive", {
    "provider": "google",
    "scopes": ["https://www.googleapis.com/auth/drive.file"],
    "auth_params": {
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    },
    "on_complete": lambda handler, user_info, tokens: existing_hook(
        user_info["sub"],
        user_info["email"],
        tokens.get("refresh_token"),
        tokens.get("scope", ""),
    ),
})
```

The authorization request this produces is equivalent to the one
`start_drive_consent` used to build — same endpoint, same scopes, same
parameters and values. Only the order in which the query string encodes
them differs, which OAuth does not treat as significant.
