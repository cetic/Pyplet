"""Structural test for the app-declared ``routes()`` hook.

WHAT THIS PROVES
================
``ServerApplication.routes()`` lets an app declare its own Tornado handlers.
The feature is worth exactly what the merge into ``_app_spec["handlers"]`` is
worth, and that merge is silent on failure: a route spliced AFTER the terminal
catch-all ``r"/.*"`` redirect, or merged after the Tornado ``Application`` was
built, leaves a server that boots, logs nothing and answers 302 on every
declared route. The rest of the suite cannot see it — nothing else exercises
``_merge_app_declared_routes()``.

So this test declares an app exposing ``routes()`` and pins the two properties
that make the hook real:

  (a) **the declared route is reachable** — ``GET`` on it answers 200 from the
      app's own handler, not a 302 from the catch-all;
  (b) **the catch-all stays last** — the declared route precedes ``r"/.*"``
      in ``_app_spec["handlers"]`` and ``r"/.*"`` is still the final entry, so
      unknown paths keep redirecting.

The module-level ``_app_spec`` and ``server_applications`` are mutated, so both
are snapshotted in ``setUp`` and restored in ``tearDown``.
"""

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, RequestHandler

from pyplet.server._server import (
    ServerApplication,
    _app_spec,
    _merge_app_declared_routes,
    server_applications,
)

_PROBE_PATTERN = r"/__routes_hook_probe__"
_PROBE_BODY = "declared-route-reached"


class _ProbeHandler(RequestHandler):
    """Minimal handler an app would contribute through ``routes()``."""

    def get(self):
        self.write(_PROBE_BODY)


class _ProbeApp(ServerApplication):
    """App declaring one custom route.

    Defined in a test module, so ``__init_subclass__`` does not register it
    (registration only fires for ``_pyplet_apps.<project>.<app>_server``
    modules); the instance is put in ``server_applications`` explicitly.
    """

    def routes(self):
        return [(_PROBE_PATTERN, _ProbeHandler, {})]


class AppDeclaredRouteTest(AsyncHTTPTestCase):
    """The declared route is reachable and the catch-all stays last."""

    def setUp(self):
        self._saved_handlers = list(_app_spec["handlers"])
        self._saved_apps = dict(server_applications)
        server_applications[("probe_project", "probe_app")] = _ProbeApp()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        _app_spec["handlers"][:] = self._saved_handlers
        server_applications.clear()
        server_applications.update(self._saved_apps)

    def get_app(self) -> Application:
        # Same sequence as astart(): merge the app-declared routes into
        # _app_spec FIRST, then build the Application from it. Merging after
        # this point would not reach the running server.
        _merge_app_declared_routes()
        return Application(**_app_spec)

    def test_declared_route_reachable_and_catchall_last(self):
        """Declared route answers 200; ``r"/.*"`` remains the last entry."""
        patterns = [entry[0] for entry in _app_spec["handlers"]]

        assert _PROBE_PATTERN in patterns, (
            "routes() was not merged into _app_spec['handlers'] — the hook "
            "is dead"
        )
        assert r"/.*" in patterns, "catch-all r'/.*' missing from _app_spec"
        assert patterns.index(_PROBE_PATTERN) < patterns.index(r"/.*"), (
            "a declared route listed after the catch-all is shadowed into a "
            "redirect"
        )
        assert patterns[-1] == r"/.*", (
            "the catch-all r'/.*' must stay the last handler, or unknown "
            "paths stop redirecting"
        )

        # follow_redirects=False so a regression surfaces as a 3xx code
        # instead of being silently followed to the login/index page.
        resp = self.fetch(_PROBE_PATTERN, follow_redirects=False)
        assert resp.code == 200, (
            f"declared route should answer 200, got {resp.code} — the "
            "catch-all or the auth gate took the request"
        )
        assert resp.body.decode("utf-8") == _PROBE_BODY, (
            "the app's own handler did not answer"
        )

        # The catch-all still works for anything undeclared.
        unknown = self.fetch(
            "/__nothing_declares_this__", follow_redirects=False
        )
        assert unknown.code in (301, 302), (
            f"unknown path should still hit the catch-all redirect, got "
            f"{unknown.code}"
        )
