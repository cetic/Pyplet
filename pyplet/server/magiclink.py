"""
pyplet.server.magiclink
=======================

Passwordless "magic link" authentication for Pyplet.

Flow
----
1. User submits their e-mail address on the login page
   → POST /auth/email
2. Server generates a single-use, time-limited token, stores it in memory,
   and sends an e-mail containing a link to /auth/verify?token=<token>
3. User clicks the link in their inbox
   → GET /auth/verify?token=<token>
4. Server validates the token (existence + expiry + single-use), sets the
   session cookie, and redirects to the originally requested page.

Configuration (environment variables)
--------------------------------------
MAGICLINK_SMTP_HOST      SMTP server hostname (required to enable magic-link)
MAGICLINK_SMTP_PORT      SMTP port (default: 587)
MAGICLINK_SMTP_USER      SMTP login username (required)
MAGICLINK_SMTP_PASSWORD  SMTP login password (required)
MAGICLINK_SMTP_TLS       Use STARTTLS — "1" (default) or "0" for plain SMTP
MAGICLINK_FROM           Sender address (defaults to MAGICLINK_SMTP_USER)
MAGICLINK_TOKEN_TTL      Token validity in seconds (default: 900 = 15 min)

Magic-link auth can coexist with OAuth providers: the login page shows all
available methods.
"""

from __future__ import annotations

import asyncio
import email.mime.multipart
import email.mime.text
import logging
import secrets
import smtplib
import time
from urllib.parse import urljoin

from . import oauth  # for set_session and _error
from . import config

logger = logging.getLogger("pyplet.server.magiclink")

# Register with oauth so that auth_enabled() returns True when magic-link
# env vars are set, even when no OAuth provider is configured.
oauth.register_auth_check(lambda: enabled())


# ---------------------------------------------------------------------------
# Enable check
# ---------------------------------------------------------------------------


def enabled() -> bool:
    """True when all required SMTP config vars are set."""
    return bool(
        config.magiclink_smtp_host
        and config.magiclink_smtp_user
        and config.magiclink_smtp_password
    )


# ---------------------------------------------------------------------------
# Token store  (in-process; replaced on restart — intentionally)
# ---------------------------------------------------------------------------

# token → {"email": str, "next": str, "exp": float, "used": bool}
_tokens: dict[str, dict] = {}

# Sweep expired tokens every time a new one is created (lazy GC).
_MAX_STORE = 10_000


def _purge_expired() -> None:
    now = time.monotonic()
    expired = [t for t, v in _tokens.items() if v["exp"] < now]
    for t in expired:
        del _tokens[t]
    # Hard cap — evict oldest if store is still too large
    if len(_tokens) > _MAX_STORE:
        oldest = sorted(_tokens, key=lambda t: _tokens[t]["exp"])[
            : len(_tokens) - _MAX_STORE
        ]
        for t in oldest:
            del _tokens[t]


def _issue_token(email_addr: str, next_url: str) -> str:
    _purge_expired()
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "email": email_addr.lower().strip(),
        "next": next_url,
        "exp": time.monotonic() + config.magiclink_token_ttl,
        "used": False,
    }
    return token


def _consume_token(token: str) -> dict | None:
    """
    Validate and consume *token*.

    Returns the token payload on success, or None if the token is unknown,
    expired, or already used.
    """
    entry = _tokens.get(token)
    if entry is None:
        return None
    if entry["used"]:
        logger.warning("Magic-link token reuse attempt for %s", entry["email"])
        return None
    if time.monotonic() > entry["exp"]:
        del _tokens[token]
        return None
    entry["used"] = True
    return entry


# ---------------------------------------------------------------------------
# E-mail delivery (blocking SMTP — run in a thread so we don't block the loop)
# ---------------------------------------------------------------------------


def _send_email_sync(to_addr: str, base: str, magic_url: str) -> None:
    """Send the magic-link e-mail synchronously (called from a thread)."""
    ttl_min = config.magiclink_token_ttl // 60

    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["Subject"] = "Your Pyplet sign-in link"
    msg["From"] = base
    msg["To"] = to_addr

    plain = (
        f"Click the link below to sign in to Pyplet.\n\n"
        f"{magic_url}\n\n"
        f"This link expires in {ttl_min} minute(s) and "
        "can only be used once.\nIf you did not request "
        "this, you can safely ignore this e-mail."
    )
    html = f"""\
<html><body>
<p>Click the button below to sign in to Pyplet.</p>
<p style="margin:24px 0">
  <a href="{magic_url}"
     style="background:#0d6efd;color:#fff;padding:12px 24px;
            border-radius:6px;text-decoration:none;font-size:16px">
    Sign in to Pyplet
  </a>
</p>
<p style="color:#6c757d;font-size:13px">
  This link expires in {ttl_min} minute(s) and can only be used once.<br>
  If you did not request this, you can safely ignore this e-mail.
</p>
</body></html>"""

    msg.attach(email.mime.text.MIMEText(plain, "plain"))
    msg.attach(email.mime.text.MIMEText(html, "html"))

    host = config.magiclink_smtp_host
    port = config.magiclink_smtp_port
    use_tls = config.magiclink_smtp_tls != "0"

    if use_tls:
        smtp = smtplib.SMTP(host, port, timeout=10)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
    else:
        smtp = smtplib.SMTP(host, port, timeout=10)

    try:
        smtp.login(config.magiclink_smtp_user, config.magiclink_smtp_password)
        smtp.sendmail(msg["From"], [to_addr], msg.as_string())
        logger.info("Magic link sent to %s", to_addr)
    finally:
        smtp.quit()


async def _send_email(to_addr: str, base: str, magic_url: str) -> None:
    """Async wrapper — runs the blocking SMTP call in a thread pool."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, _send_email_sync, to_addr, base, magic_url
    )


# ---------------------------------------------------------------------------
# Request handlers (called from _server.py)
# ---------------------------------------------------------------------------


async def handle_request(handler) -> None:
    """
    POST /auth/email

    Accepts ``email`` form field, issues a token, sends the magic-link e-mail,
    then renders an "e-mail sent" confirmation page.
    """
    email_addr = (handler.get_argument("email", "") or "").strip().lower()

    if not email_addr or "@" not in email_addr:
        oauth._error(handler, 400, "Please enter a valid e-mail address.")
        return

    next_url = handler.get_argument("next", "/")
    token = _issue_token(email_addr, next_url)

    base = config.url or f"{handler.request.protocol}://{handler.request.host}"
    magic_url = urljoin(base, f"/auth/verify?token={token}")

    try:
        await _send_email(email_addr, base, magic_url)
    except Exception as exc:
        logger.error("Failed to send magic-link to %s: %s", email_addr, exc)
        oauth._error(
            handler,
            502,
            "Could not send the sign-in e-mail. "
            "Please try again or use another sign-in method.",
        )
        return

    # Show confirmation — don't reveal whether the address exists in any ACL.
    from . import templates

    handler.write(
        str(templates.magiclink_sent_template(handler, email_addr)).encode(
            "UTF-8"
        )
    )


async def handle_verify(handler) -> None:
    """
    GET /auth/verify?token=<token>

    Validates the token, sets the session, and redirects.
    """
    token = handler.get_argument("token", "")
    entry = _consume_token(token)

    if entry is None:
        oauth._error(
            handler,
            400,
            "This sign-in link is invalid, expired, or has already been used. "
            "Please request a new one.",
        )
        return

    email_addr = entry["email"]
    next_url = entry["next"]

    user_info = {
        "sub": email_addr,
        "email": email_addr,
        "name": email_addr,
        "picture": "",
        "provider": "magiclink",
    }

    oauth.set_session(handler, user_info)
    logger.info("Magic-link login: %s", email_addr)
    handler.redirect(next_url)
