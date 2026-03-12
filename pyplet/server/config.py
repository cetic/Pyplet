import os

# Generate params dynamically from the module's attributes
params = [
    name
    for name, _ in globals().items()
    if not name.startswith("_") and name != "params"
]

address = os.environ.get("PYPLET_ADDR", "127.0.0.1")
apps = os.environ.get("PYPLET_APPS", "apps")
debug = os.environ.get("PYPLET_DEBUG", "1")
port = os.environ.get("PYPLET_PORT", "8080")
pyodide_url = os.environ.get(
    "PYPLET_PYODIDE",
    "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js",
)
url = os.environ.get("PYPLET_URL", None)

# ── Authentication ────────────────────────────────────────────────────────────
# Signs session cookies.  Generate with:
#   python -c "import secrets; print(secrets.token_hex(32))"
# Without this, a random secret is generated at startup (sessions lost on restart).
oauth_cookie_secret = os.environ.get("PYPLET_COOKIE_SECRET", None)

# Google OAuth2 credentials
# Register at: https://console.cloud.google.com/apis/credentials
oauth_google_client_id = os.environ.get("OAUTH_GOOGLE_CLIENT_ID", None)
oauth_google_client_secret = os.environ.get("OAUTH_GOOGLE_CLIENT_SECRET", None)

# Microsoft / Entra ID credentials
# Register at: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps
oauth_microsoft_client_id = os.environ.get("OAUTH_MICROSOFT_CLIENT_ID", None)
oauth_microsoft_client_secret = os.environ.get(
    "OAUTH_MICROSOFT_CLIENT_SECRET", None
)
# Tenant ID or "common" for multi-tenant apps
oauth_microsoft_tenant = os.environ.get("OAUTH_MICROSOFT_TENANT", "common")

# ── Magic-link e-mail auth ────────────────────────────────────────────────────
# Configure an SMTP server to enable passwordless magic-link login.
# All four of host/port/user/password must be set to enable magic-link auth.
magiclink_smtp_host = os.environ.get("MAGICLINK_SMTP_HOST", None)
magiclink_smtp_port = int(os.environ.get("MAGICLINK_SMTP_PORT", "587"))
magiclink_smtp_user = os.environ.get("MAGICLINK_SMTP_USER", None)
magiclink_smtp_password = os.environ.get("MAGICLINK_SMTP_PASSWORD", None)
# Set to "0" to use plain SMTP (not recommended); default is STARTTLS.
magiclink_smtp_tls = os.environ.get("MAGICLINK_SMTP_TLS", "1")
# Sender address shown to the recipient (defaults to smtp user).
magiclink_from = os.environ.get("MAGICLINK_FROM", magiclink_smtp_user)
# How long (in seconds) a magic link remains valid (default: 15 minutes).
magiclink_token_ttl = int(os.environ.get("MAGICLINK_TOKEN_TTL", "900"))

# ── ACL rules ─────────────────────────────────────────────────────────────────
# Path to the ACL rules JSON file (default: <apps_dir>/auth_rules.json).
# Each entry is [project_regex, app_regex, email_regex].
# If the file does not exist, all authenticated users can access all apps.
auth_rules_file = os.environ.get(
    "PYPLET_AUTH_RULES_FILE",
    os.path.join(apps, "auth_rules.json"),
)
