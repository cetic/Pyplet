"""pyplet-CORE app-static path-traversal tests (qs-port security hardening).

WHAT THIS PROVES
================
The ``/apps/<project>/static/<tail>`` route serves each app's static assets.
It used to register a single Tornado ``StaticFileHandler`` rooted at the whole
``apps/`` tree with a ONE-group regex
(``/apps/([a-zA-Z_][a-zA-Z0-9_]*/static/.*)``). Tornado's
``validate_absolute_path`` only prevents escaping ``root`` (``apps/``), so a
``..`` in the captured tail escaped the intended per-app ``static/`` dir while
staying under ``apps/`` — an unauthenticated path traversal that leaked every
app's server source (``*_server.py``) and the ACL file (``auth_rules.json``).

The fix roots the handler at ``<apps>/<project>/static`` PER REQUEST
(``AppStaticFileHandler`` + a two-group regex). This pins:

  (a) a legitimate static file still serves (200);
  (b) ``..`` traversal to a sibling ``*_server.py`` is refused (NOT 200);
  (c) ``..`` traversal up to ``auth_rules.json`` is refused (NOT 200);
  (d) the percent-encoded ``%2e%2e`` variant is also refused (NOT 200);
  (e) an absolute tail (``static//etc/hosts``) is refused (NOT 200);
  (f) the route regex captures project + tail as two groups (structural guard),
      read from ``_app_spec`` itself so a revert to the one-group form fails.

Rooting per-app is not enough on its own: Tornado's containment test is purely
LEXICAL (``abspath`` prefix compare, never ``realpath``), so a symlink planted
in an app's ``static/`` dir was served whatever it pointed at, including files
outside ``apps/`` entirely — an unauthenticated arbitrary-file read. The
handler therefore overrides ``validate_absolute_path`` to re-check the
symlink-resolved paths. This also pins:

  (g) a symlink out of ``static/`` is refused, by GET and by HEAD (NOT 200);
  (h) a read *through* a symlinked directory is refused (NOT 200);
  (i) a symlink resolving INSIDE ``static/`` still serves (200) — the guard
      refuses escapes only, internal symlinks are not collateral damage.

Self-contained: a temp apps/ tree is built with one app that has a ``static/``
file, plus a sibling ``*_server.py`` and an ``auth_rules.json`` as traversal
targets, and symlinks into a second temp dir outside the tree as symlink bait.
Uses Tornado's ``AsyncHTTPTestCase`` harness (shipped with the existing
``tornado`` dep — no new dependency), mirroring ``healthz_test.py``.
"""

import os
import tempfile

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from pyplet.server._server import _app_spec


def _handler_patterns() -> list[str]:
    """Pattern strings of ``_app_spec['handlers']``, in declared order."""
    return [entry[0] for entry in _app_spec["handlers"]]


def _static_route_entry() -> tuple:
    """The single ``_app_spec`` entry serving ``/apps/<project>/static/``."""
    entries = [e for e in _app_spec["handlers"] if "/static/" in e[0]]
    assert len(entries) == 1, f"expected one app-static route, got {entries!r}"
    return entries[0]


def test_app_static_route_captures_project_and_tail_separately():
    """The static route must capture project + tail as two groups.

    A single group spanning ``<project>/static/<tail>`` cannot be rooted
    per-app, which is exactly what let ``..`` escape. This structural guard
    fails if someone reverts the regex to the vulnerable one-group form.
    """
    patterns = _handler_patterns()
    static_routes = [p for p in patterns if "/static/" in p]
    assert static_routes == [r"/apps/([a-zA-Z_][a-zA-Z0-9_]*)/static/(.*)"], (
        "app static route must capture project and file tail separately; "
        f"got {static_routes!r}"
    )


class AppStaticTraversalTest(AsyncHTTPTestCase):
    """Real-HTTP assertions against a temp apps/ tree with a traversal bait."""

    def setUp(self):
        # Build the temp apps/ tree BEFORE AsyncHTTPTestCase.setUp() calls
        # get_app(), which needs self._apps_root.
        self._tmp = tempfile.TemporaryDirectory()
        apps_root = self._tmp.name
        self._apps_root = apps_root

        app_static = os.path.join(apps_root, "DemoApp", "static")
        os.makedirs(app_static)
        with open(os.path.join(app_static, "d3.v7.min.js"), "w") as f:
            f.write("// legit static asset\n")

        # Bait files a traversal would target.
        with open(
            os.path.join(apps_root, "DemoApp", "DemoApp_server.py"), "w"
        ) as f:
            f.write("SECRET = 'server-side source that must not leak'\n")
        with open(os.path.join(apps_root, "auth_rules.json"), "w") as f:
            f.write('{"acl": "must not leak"}\n')

        # A symlink bait: a file OUTSIDE the apps/ tree entirely, reachable
        # only if the containment test is lexical (see the symlink tests).
        self._outside = tempfile.TemporaryDirectory()
        outside_secret = os.path.join(self._outside.name, "id_rsa")
        with open(outside_secret, "w") as f:
            f.write("OUTSIDE-PRIVATE-KEY must not leak\n")
        os.symlink(outside_secret, os.path.join(app_static, "link_file"))
        os.symlink(self._outside.name, os.path.join(app_static, "link_dir"))
        # A symlink that stays INSIDE static/ must keep working.
        os.symlink(
            os.path.join(app_static, "d3.v7.min.js"),
            os.path.join(app_static, "alias.js"),
        )

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self._tmp.cleanup()
        self._outside.cleanup()

    def get_app(self) -> Application:
        # Take the PRODUCTION route entry (regex, handler class, kwarg name)
        # from `_app_spec` and only redirect its root at the temp tree. A
        # hand-copied entry here would keep passing if production swapped the
        # handler or the regex back to the vulnerable one-group form.
        pattern, handler, kwargs = _static_route_entry()
        return Application(
            [(pattern, handler, {**kwargs, "apps_root": self._apps_root})]
        )

    def test_legit_static_file_is_served(self):
        """A real per-app static asset still returns 200."""
        resp = self.fetch("/apps/DemoApp/static/d3.v7.min.js")
        assert resp.code == 200, (
            f"legit static file should serve 200, got {resp.code}"
        )
        assert b"legit static asset" in resp.body

    def test_traversal_to_sibling_server_source_blocked(self):
        """``..`` up to the sibling ``*_server.py`` must NOT return 200."""
        resp = self.fetch(
            "/apps/DemoApp/static/../DemoApp_server.py",
            follow_redirects=False,
        )
        assert resp.code != 200, (
            "traversal to *_server.py must be refused, got 200 "
            f"(body={resp.body!r})"
        )
        assert b"SECRET" not in resp.body
        assert resp.code in (403, 404), (
            f"expected 403/404 for traversal, got {resp.code}"
        )

    def test_traversal_to_auth_rules_blocked(self):
        """``../../auth_rules.json`` must NOT return 200."""
        resp = self.fetch(
            "/apps/DemoApp/static/../../auth_rules.json",
            follow_redirects=False,
        )
        assert resp.code != 200, (
            "traversal to auth_rules.json must be refused, got 200 "
            f"(body={resp.body!r})"
        )
        assert b"must not leak" not in resp.body

    def test_percent_encoded_traversal_blocked(self):
        """The percent-encoded ``%2e%2e`` variant must NOT return 200."""
        resp = self.fetch(
            "/apps/DemoApp/static/%2e%2e/DemoApp_server.py",
            follow_redirects=False,
        )
        assert resp.code != 200, (
            "percent-encoded traversal must be refused, got 200 "
            f"(body={resp.body!r})"
        )
        assert b"SECRET" not in resp.body

    def test_absolute_path_escape_blocked(self):
        """An absolute tail (``static//etc/hosts``) must NOT return 200.

        The other traversal tests all use ``..``/``%2e%2e``. A refactor that
        strips the leading slash off the tail before joining would regress
        this silently, so it gets its own assertion.
        """
        resp = self.fetch(
            "/apps/DemoApp/static//etc/hosts", follow_redirects=False
        )
        assert resp.code != 200, (
            "absolute-path escape must be refused, got 200 "
            f"(body={resp.body!r})"
        )

    def test_symlink_out_of_static_dir_blocked(self):
        """A symlink to a file outside ``apps/`` must NOT be served.

        Tornado's containment check is purely LEXICAL (``abspath`` prefix
        compare, never ``realpath``), so before the
        ``validate_absolute_path`` override a symlink planted in an app's
        ``static/`` dir was served whatever it pointed at — an
        unauthenticated arbitrary-file read, worse than the ``..`` traversal
        the per-request root closes.
        """
        resp = self.fetch(
            "/apps/DemoApp/static/link_file", follow_redirects=False
        )
        assert resp.code != 200, (
            "symlink out of static/ must be refused, got 200 "
            f"(body={resp.body!r})"
        )
        assert b"OUTSIDE-PRIVATE-KEY" not in resp.body

    def test_symlinked_directory_out_of_static_dir_blocked(self):
        """Reaching through a symlinked *directory* must NOT be served."""
        resp = self.fetch(
            "/apps/DemoApp/static/link_dir/id_rsa", follow_redirects=False
        )
        assert resp.code != 200, (
            "read through a symlinked dir must be refused, got 200 "
            f"(body={resp.body!r})"
        )
        assert b"OUTSIDE-PRIVATE-KEY" not in resp.body

    def test_head_symlink_out_of_static_dir_blocked(self):
        """HEAD goes through the same guard as GET."""
        resp = self.fetch(
            "/apps/DemoApp/static/link_file",
            method="HEAD",
            follow_redirects=False,
        )
        assert resp.code != 200, (
            f"HEAD on an escaping symlink must be refused, got {resp.code}"
        )

    def test_symlink_inside_static_dir_still_served(self):
        """A symlink that resolves INSIDE static/ keeps working.

        The guard refuses escapes only; internal symlinks (a common way to
        pin an asset version) must not become collateral damage.
        """
        resp = self.fetch("/apps/DemoApp/static/alias.js")
        assert resp.code == 200, (
            f"symlink inside static/ should serve 200, got {resp.code}"
        )
        assert b"legit static asset" in resp.body

    def test_head_legit_static_file_is_served(self):
        """HEAD on a real asset: 200, empty body, matching Content-Length.

        Tornado dispatches every method as ``method(*path_args)``; the
        two-group route means HEAD is called with (project, tail). Without a
        matching ``head`` override the inherited
        ``StaticFileHandler.head(self, path)`` got two positional args and
        raised TypeError -> HTTP 500. This pins the fix: HEAD works and its
        Content-Length matches the GET body length.
        """
        get_resp = self.fetch("/apps/DemoApp/static/d3.v7.min.js")
        assert get_resp.code == 200
        head_resp = self.fetch(
            "/apps/DemoApp/static/d3.v7.min.js", method="HEAD"
        )
        assert head_resp.code == 200, (
            "HEAD on a legit static file should serve 200, got "
            f"{head_resp.code} (body={head_resp.body!r})"
        )
        assert head_resp.body == b"", (
            f"HEAD response body must be empty, got {head_resp.body!r}"
        )
        assert head_resp.headers.get("Content-Length") == str(
            len(get_resp.body)
        ), (
            "HEAD Content-Length must match GET body length; got "
            f"{head_resp.headers.get('Content-Length')!r} vs "
            f"{len(get_resp.body)}"
        )

    def test_head_traversal_to_sibling_server_source_blocked(self):
        """HEAD ``..`` to the sibling ``*_server.py`` must NOT return 200."""
        resp = self.fetch(
            "/apps/DemoApp/static/../DemoApp_server.py",
            method="HEAD",
            follow_redirects=False,
        )
        assert resp.code != 200, (
            "HEAD traversal to *_server.py must be refused, got 200"
        )
        assert resp.code in (403, 404), (
            f"expected 403/404 for HEAD traversal, got {resp.code}"
        )

    def test_app_without_static_dir_does_not_crash(self):
        """An app with no static/ dir 404s rather than erroring."""
        resp = self.fetch(
            "/apps/NoSuchApp/static/whatever.js", follow_redirects=False
        )
        assert resp.code == 404, (
            f"missing static dir should 404, got {resp.code}"
        )
