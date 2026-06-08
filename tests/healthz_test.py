"""Liveness route tests (Story 18.6 — OBSERV-3).

WHAT THIS PROVES
================
Story 18.6 adds an **unauthenticated** ``GET /healthz`` liveness route to the
pyplet-core Tornado handler table (``_server._app_spec["handlers"]``) so an
LB / systemd / k8s probe can tell a live process from a dead one without
authenticating. The route is process-up only (no DB / provider / loop checks —
those belong in an application-level ``/readyz``). This test pins three
properties:

  (a) **answers 200 unauthenticated** — a plain handler (NOT ``_AuthMixin``)
      so ``GET /healthz`` returns 200 with a small JSON body and does NOT
      302→``/``→``/login``;
  (b) **routed before the catch-all** — ``/healthz`` precedes the terminal
      ``r"/.*"`` ``RedirectHandler`` in ``_app_spec["handlers"]`` (else the
      catch-all would shadow it into a redirect), and the catch-all stays last;
  (c) **unauthenticated by construction** — ``HealthzHandler`` does not
      subclass ``_AuthMixin`` (the auth gate), so no auth surface is added.

These are sync ``def test_*`` functions; the HTTP assertion uses Tornado's
``AsyncHTTPTestCase`` harness which ships with the existing ``tornado`` dep —
no new dependency.
"""

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from pyplet.server._server import HealthzHandler, _app_spec, _AuthMixin


def _handler_patterns() -> list[str]:
    """Pattern strings of ``_app_spec['handlers']``, in declared order."""
    return [entry[0] for entry in _app_spec["handlers"]]


def test_healthz_precedes_catchall():
    """``/healthz`` is registered before the terminal ``r"/.*"`` catch-all.

    The catch-all ``RedirectHandler`` must stay the LAST entry; a ``/healthz``
    listed earlier is matched first, so the probe gets 200 instead of a
    302→``/``. If this inverts, the route silently becomes a redirect.
    """
    patterns = _handler_patterns()
    assert r"/healthz" in patterns, "/healthz route missing from _app_spec"
    assert r"/.*" in patterns, "catch-all r'/.*' missing from _app_spec"
    assert patterns.index(r"/healthz") < patterns.index(r"/.*"), (
        "/healthz must precede the catch-all r'/.*' or it gets shadowed "
        "into a redirect"
    )
    assert patterns[-1] == r"/.*", "the catch-all r'/.*' must stay last"


def test_healthz_handler_is_unauthenticated_by_construction():
    """``HealthzHandler`` must NOT subclass ``_AuthMixin`` (no auth gate).

    A liveness probe must answer without a session; inheriting the auth mixin
    would gate it behind ``_require_auth`` (302/401). This is the structural
    guarantee that no auth surface is added.
    """
    assert not issubclass(HealthzHandler, _AuthMixin), (
        "HealthzHandler must not subclass _AuthMixin — /healthz is "
        "unauthenticated by construction"
    )


class HealthzRouteTest(AsyncHTTPTestCase):
    """Real-HTTP assertion: ``GET /healthz`` answers 200, no auth."""

    def get_app(self) -> Application:
        # Build a real Tornado app from the core handler table. astart() is
        # NOT called, so no app-declared routes are spliced — /healthz is a
        # static entry in _app_spec and is reachable on its own.
        return Application(**_app_spec)

    def test_healthz_returns_200_without_auth(self):
        """``GET /healthz`` ⇒ 200 + JSON body, no redirect, no cookie sent."""
        # follow_redirects=False so a (regression) 302→/login surfaces as a
        # 3xx code rather than being silently followed to the login page.
        resp = self.fetch("/healthz", follow_redirects=False)
        assert resp.code == 200, (
            f"/healthz should answer 200 unauthenticated, got {resp.code}"
        )
        body = resp.body.decode("utf-8")
        assert "ok" in body, f"expected a tiny 'ok' body, got {body!r}"
