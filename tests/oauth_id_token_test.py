"""id_token JWKS signature-verification tests (Story 18.19, SECURI-8).

Exercises the pure, synchronous ``oauth._verify_id_token_against_jwks`` with
crafted JWTs signed by a test RSA key and a JWKS built from that key's public
half — no async, no network. Mirrors ``tests/oauth_test.py`` (sync ``def
test_*`` + ``monkeypatch``); ``authlib`` (already a dependency) mints the keys
and signs the tokens.

A valid token verifies; a bad signature, a wrong ``aud``, a wrong ``iss``, an
expired ``exp``, or a non-RS256 algorithm is rejected. Google's bare-host
``iss`` variant (``accounts.google.com``) is accepted. The async wrapper
``_verify_id_token_claims`` is covered too — the discovery + JWKS fetches are
stubbed so no real HTTP happens — including the key-rotation single-refetch
path and the "do NOT refetch on a claim failure" amplification guard.

``authlib.jose`` emits an ``AuthlibDeprecationWarning`` (superseded by
``joserfc`` in authlib 2.0 — migrating is out of scope); the module-level
filter keeps it from failing under a warnings-as-errors run.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from authlib.jose import JsonWebKey, JsonWebToken
from authlib.jose.errors import JoseError

from pyplet.server import oauth

pytestmark = pytest.mark.filterwarnings(
    "ignore:authlib.jose module is deprecated"
)

_RS = JsonWebToken(["RS256"])
_ISSUER = "https://accounts.google.com"
_AUDIENCE = "client-id.apps.googleusercontent.com"


def _make_key() -> JsonWebKey:
    """Return a fresh private RSA ``JsonWebKey`` (a signing key)."""
    return JsonWebKey.generate_key("RSA", 2048, is_private=True)


def _jwks(key: JsonWebKey, kid: str = "k1") -> dict:
    """Build a JWKS dict (``{"keys": [...]}``) from *key*'s public half."""
    return {"keys": [key.as_dict(is_private=False, kid=kid)]}


def _sign(key: JsonWebKey, claims: dict, *, kid: str = "k1") -> str:
    """Sign *claims* into a compact RS256 JWT with *key* (kid in header)."""
    token = _RS.encode({"alg": "RS256", "kid": kid}, claims, key)
    return token.decode() if isinstance(token, bytes) else token


def _claims(**overrides) -> dict:
    """A baseline valid claim set; override individual fields per test."""
    base = {
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "exp": int(time.time()) + 3600,
        "sub": "1234567890",
        "email": "user@example.com",
        "name": "Test User",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Pure verifier — the crafted-JWT-vs-stubbed-JWKS cases (a)-(f) + alg restrict
# ---------------------------------------------------------------------------


def test_valid_token_returns_claims():
    """(a) Good signature + correct iss/aud + future exp ⇒ claims returned."""
    key = _make_key()
    token = _sign(key, _claims())
    out = oauth._verify_id_token_against_jwks(
        token, _jwks(key), issuer=_ISSUER, audience=_AUDIENCE
    )
    assert out["sub"] == "1234567890"
    assert out["email"] == "user@example.com"


def test_bad_signature_rejected():
    """(b) Signed by a DIFFERENT key than the JWKS advertises ⇒ rejected."""
    signing_key = _make_key()
    advertised_key = _make_key()
    token = _sign(signing_key, _claims())  # kid=k1, signed by signing_key
    jwks = _jwks(advertised_key)  # kid=k1 maps to a different public key
    with pytest.raises(JoseError):
        oauth._verify_id_token_against_jwks(
            token, jwks, issuer=_ISSUER, audience=_AUDIENCE
        )


def test_wrong_audience_rejected():
    """(c) aud does not match the configured client_id ⇒ rejected."""
    key = _make_key()
    token = _sign(key, _claims(aud="someone-else.apps.googleusercontent.com"))
    with pytest.raises(JoseError):
        oauth._verify_id_token_against_jwks(
            token, _jwks(key), issuer=_ISSUER, audience=_AUDIENCE
        )


def test_wrong_issuer_rejected():
    """(d) iss is not an accepted issuer ⇒ rejected."""
    key = _make_key()
    token = _sign(key, _claims(iss="https://evil.example.com"))
    with pytest.raises(JoseError):
        oauth._verify_id_token_against_jwks(
            token, _jwks(key), issuer=_ISSUER, audience=_AUDIENCE
        )


def test_expired_token_rejected():
    """(e) exp is in the past ⇒ rejected."""
    key = _make_key()
    token = _sign(key, _claims(exp=int(time.time()) - 60))
    with pytest.raises(JoseError):
        oauth._verify_id_token_against_jwks(
            token, _jwks(key), issuer=_ISSUER, audience=_AUDIENCE
        )


def test_google_bare_host_issuer_accepted():
    """(f) Google's bare-host iss (accounts.google.com) verifies against the
    https:// discovery issuer."""
    key = _make_key()
    token = _sign(key, _claims(iss="accounts.google.com"))
    out = oauth._verify_id_token_against_jwks(
        token, _jwks(key), issuer=_ISSUER, audience=_AUDIENCE
    )
    assert out["sub"] == "1234567890"


def test_non_rs256_algorithm_rejected():
    """An HS256-signed token (alg-confusion payload) is rejected — the RS256
    whitelist closes alg-confusion even with a guessable HMAC secret."""
    rsa_key = _make_key()
    pub = rsa_key.as_dict(is_private=False, kid="k1")
    # Canonical attack: forge an HS256 token using the public-key material as
    # the HMAC secret. The verifier must reject on the algorithm alone.
    forged = JsonWebToken(["HS256"]).encode(
        {"alg": "HS256", "kid": "k1"}, _claims(), json.dumps(pub).encode()
    )
    forged = forged.decode() if isinstance(forged, bytes) else forged
    with pytest.raises((JoseError, ValueError)):
        oauth._verify_id_token_against_jwks(
            forged, _jwks(rsa_key), issuer=_ISSUER, audience=_AUDIENCE
        )


# ---------------------------------------------------------------------------
# Async wrapper — stubbed discovery + JWKS fetches (no real HTTP)
# ---------------------------------------------------------------------------


def _stub_fetches(monkeypatch, jwks_for):
    """Stub ``_fetch_oidc_config`` + ``_fetch_jwks`` + the google client_id.

    ``jwks_for`` is a callable ``(force_refresh: bool) -> dict`` so a test can
    return a different keyset on the forced refetch (key-rotation simulation).
    Returns a ``calls`` dict counting ``_fetch_jwks`` invocations.
    """
    calls = {"jwks": 0}

    async def _fake_oidc(provider):
        return {"issuer": _ISSUER, "jwks_uri": "https://example/jwks"}

    async def _fake_jwks(provider, *, force_refresh=False):
        calls["jwks"] += 1
        return jwks_for(force_refresh)

    monkeypatch.setattr(oauth, "_fetch_oidc_config", _fake_oidc)
    monkeypatch.setattr(oauth, "_fetch_jwks", _fake_jwks)
    monkeypatch.setitem(
        oauth._PROVIDER_CONFIGS["google"], "client_id", lambda: _AUDIENCE
    )
    return calls


def test_async_wrapper_verifies_with_stubbed_fetches(monkeypatch):
    """Async wrapper resolves issuer/audience + JWKS and verifies a token."""
    key = _make_key()
    token = _sign(key, _claims())
    calls = _stub_fetches(monkeypatch, lambda _force: _jwks(key))
    out = asyncio.run(oauth._verify_id_token_claims(token, "google"))
    assert out["sub"] == "1234567890"
    assert calls["jwks"] == 1  # verified on the first (cached) keyset


def test_async_wrapper_refetches_jwks_on_rotation(monkeypatch):
    """A signature miss against the cached keyset triggers exactly one forced
    refetch; the rotated key then verifies."""
    old_key = _make_key()
    new_key = _make_key()
    token = _sign(new_key, _claims())  # signed by the rotated key (kid=k1)
    calls = _stub_fetches(
        monkeypatch,
        lambda force: _jwks(new_key) if force else _jwks(old_key),
    )
    out = asyncio.run(oauth._verify_id_token_claims(token, "google"))
    assert out["sub"] == "1234567890"
    assert calls["jwks"] == 2  # initial cached miss + one forced refetch


def test_async_wrapper_does_not_refetch_on_claim_failure(monkeypatch):
    """A wrong-aud token (valid signature) must NOT trigger a JWKS refetch —
    refetching cannot fix a claim failure and is an amplification vector."""
    key = _make_key()
    token = _sign(key, _claims(aud="wrong-audience"))
    calls = _stub_fetches(monkeypatch, lambda _force: _jwks(key))
    with pytest.raises(JoseError):
        asyncio.run(oauth._verify_id_token_claims(token, "google"))
    assert calls["jwks"] == 1  # NO refetch on a claim failure
