"""Configuration for the Pyplet server."""

import os
from typing import Any, Callable, Optional


class Param:
    """A descriptor that holds configuration metadata
    but returns the resolved value."""

    def __init__(
        self,
        default: Any,
        description: str,
        type_cast: Callable = str,
        env_var: Optional[str] = None,
    ):
        self.default = default
        self.description = description
        self.type_cast = type_cast
        self.env_var: Optional[str] = env_var
        self.name: Optional[str] = (
            None  # Populated automatically by __set_name__
        )

    def __set_name__(self, owner, name):
        self.name = name
        # If no explicit env_var is given, default to uppercase exact match
        if not self.env_var:
            self.env_var = name.upper()

    def __get__(self, instance, owner):
        # Access via the class (PypletConfig.port)
        # returns the Param object for metadata
        if instance is None:
            return self

        # 1. Check if CLI overrode it (via setattr)
        if self.name in instance.__dict__:
            return instance.__dict__[self.name]

        # 2. Check Environment Variable
        env_val = os.environ.get(self.env_var)
        if env_val is not None:
            return self.type_cast(env_val)

        # 3. Fallback to Default
        # If default is a callable (like a lambda), evaluate it lazily
        if callable(self.default):
            return self.default(instance)

        return self.default

    def __set__(self, instance, value):
        # Save CLI overrides to the instance dictionary, casting them safely
        if value is not None:
            instance.__dict__[self.name] = self.type_cast(value)
        else:
            instance.__dict__[self.name] = None


class PypletConfig:
    # ── Core Server ──────────────────────────────────────────────────────────
    address = Param(
        default="127.0.0.1",
        description="The IP address to bind the server to.",
        env_var="PYPLET_ADDR",
    )
    apps = Param(
        default="apps",
        description="The directory containing your pyplet apps.",
        env_var="PYPLET_APPS",
    )
    debug = Param(
        default="1",
        description="Enable debug mode (1 for true, 0 for false).",
        env_var="PYPLET_DEBUG",
    )
    port = Param(
        default=8080,
        description="The port the server will listen on.",
        type_cast=int,
        env_var="PYPLET_PORT",
    )
    # pyodide_url = Param(
    #     default="https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js",
    #     description="The URL to fetch Pyodide from.",
    #     env_var="PYPLET_PYODIDE",
    # )

    url = Param(
        default=None,
        description="The URL the server will listen on.",
        env_var="PYPLET_URL",
    )

    # ── Authentication ───────────────────────────────────────────────────────
    oauth_cookie_secret = Param(
        default=None,
        description=(
            "Signs session cookies. Without this, a "
            "random secret is generated at startup."
        ),
        env_var="PYPLET_COOKIE_SECRET",
    )
    oauth_google_client_id = Param(
        default=None,
        description="Google OAuth2 client ID.",
        env_var="OAUTH_GOOGLE_CLIENT_ID",
    )
    oauth_google_client_secret = Param(
        default=None,
        description="Google OAuth2 client secret.",
        env_var="OAUTH_GOOGLE_CLIENT_SECRET",
    )
    oauth_microsoft_client_id = Param(
        default=None,
        description="Microsoft Entra ID client ID.",
        env_var="OAUTH_MICROSOFT_CLIENT_ID",
    )
    oauth_microsoft_client_secret = Param(
        default=None,
        description="Microsoft Entra ID client secret.",
        env_var="OAUTH_MICROSOFT_CLIENT_SECRET",
    )
    oauth_microsoft_tenant = Param(
        default="common",
        description='Tenant ID or "common" for multi-tenant apps.',
        env_var="OAUTH_MICROSOFT_TENANT",
    )

    # ── Magic-link e-mail auth ───────────────────────────────────────────────
    magiclink_smtp_host = Param(
        default=None,
        description=(
            "Configure an SMTP server host to enable magic-link login."
        ),
        env_var="MAGICLINK_SMTP_HOST",
    )
    magiclink_smtp_port = Param(
        default=587,
        description="SMTP server port.",
        type_cast=int,
        env_var="MAGICLINK_SMTP_PORT",
    )
    magiclink_smtp_user = Param(
        default=None,
        description="SMTP server username.",
        env_var="MAGICLINK_SMTP_USER",
    )
    magiclink_smtp_password = Param(
        default=None,
        description="SMTP server password.",
        env_var="MAGICLINK_SMTP_PASSWORD",
    )
    magiclink_smtp_tls = Param(
        default="1",
        description='Set to "0" to use plain SMTP; default is STARTTLS.',
        env_var="MAGICLINK_SMTP_TLS",
    )
    magiclink_from = Param(
        # Lazy evaluation: defaults to the user if not explicitly set
        default=lambda self: self.magiclink_smtp_user,
        description="Sender address shown to the recipient.",
        env_var="MAGICLINK_FROM",
    )
    magiclink_token_ttl = Param(
        default=900,
        description="How long (in seconds) a magic link remains valid.",
        type_cast=int,
        env_var="MAGICLINK_TOKEN_TTL",
    )

    # ── ACL rules ────────────────────────────────────────────────────────────
    auth_rules_file = Param(
        # Lazy evaluation: dynamically builds the path based on the
        # current 'apps' dir
        default=lambda self: os.path.join(self.apps, "auth_rules.json"),
        description="Path to the ACL rules JSON file.",
        env_var="PYPLET_AUTH_RULES_FILE",
    )

    @property
    def params(self) -> list[str]:
        """Dynamically generates the list of parameter names."""
        return [
            name
            for name, attr in self.__class__.__dict__.items()
            if isinstance(attr, Param)
        ]


# Expose a single instance for the rest of the application to import
config = PypletConfig()

# Expose 'params' to maintain compatibility
params = config.params
