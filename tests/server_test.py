"""
Unit tests for the default favicon injection in pyplet.server._server.

These tests verify that:
1. `load_favicon_as_data_uri` turns an SVG file into a base64 data URI
   and gracefully returns None (with a warning) when the file is missing.
2. `_has_favicon_link` correctly detects any pre-existing favicon
   `<link>` tag regardless of quoting/case/rel-value variant.
3. `BaseHandler.write_html` injects the inline SVG favicon right after
   `<head>` when none is declared, leaves an existing favicon alone,
   skips injection entirely when no favicon is configured, and does
   not crash on HTML that has no `<head>` tag.
"""

import base64
import logging

import markupsafe
import pytest
import tornado.testing
import tornado.web

from pyplet.server._server import (
    BaseHandler,
    _has_favicon_link,
    load_favicon_as_data_uri,
)

SVG_BYTES = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
FAVICON_URI = (
    f"data:image/svg+xml;base64,{base64.b64encode(SVG_BYTES).decode()}"
)


@pytest.mark.unit
class TestLoadFaviconAsDataUri:
    """Test suite for `load_favicon_as_data_uri`."""

    def test_missing_file_returns_none_and_logs_warning(
        self, tmp_path, caplog
    ):
        missing = tmp_path / "does_not_exist.svg"

        with caplog.at_level(logging.WARNING):
            result = load_favicon_as_data_uri(str(missing))

        assert result is None
        assert any(
            "not found" in record.message.lower() for record in caplog.records
        )

    def test_reads_svg_file_and_encodes_base64(self, tmp_path):
        svg_file = tmp_path / "logo.svg"
        svg_file.write_bytes(SVG_BYTES)

        result = load_favicon_as_data_uri(str(svg_file))

        assert result == FAVICON_URI
        # Round-trip: decoding the payload gives back the original bytes.
        header, _, b64_payload = result.partition(",")
        assert header == "data:image/svg+xml;base64"
        assert base64.b64decode(b64_payload) == SVG_BYTES


@pytest.mark.unit
class TestHasFaviconLink:
    """Test suite for the `_has_favicon_link` detector."""

    @pytest.mark.parametrize(
        "html_str",
        [
            '<link rel="icon" href="/favicon.ico">',
            '<link rel="shortcut icon" href="/favicon.ico">',
            '<link rel="apple-touch-icon" href="/x.png">',
            "<link rel='icon' href='/favicon.ico'>",
            "<LINK REL='ICON' HREF='/favicon.ico'>",
            '<link href="/favicon.ico" rel="icon">',
            "<link rel=icon href=/favicon.ico>",
        ],
    )
    def test_detects_existing_favicon_variants(self, html_str):
        html = f"<html><head>{html_str}</head><body></body></html>"
        assert _has_favicon_link(html) is True

    @pytest.mark.parametrize(
        "html_str",
        [
            "<html><head><title>t</title></head><body></body></html>",
            '<html><head><link rel="stylesheet" href="/s.css"></head></html>',
            "<html><head></head><body></body></html>",
        ],
    )
    def test_no_favicon_present(self, html_str):
        assert _has_favicon_link(html_str) is False


# ---------------------------------------------------------------------------
# End-to-end handler tests: exercise BaseHandler.write_html over real HTTP
# responses served by a minimal, standalone Tornado application.
# ---------------------------------------------------------------------------


class _NoFaviconHandler(BaseHandler):
    def get(self):
        self.write_html(
            "<html><head><title>t</title></head><body>hi</body></html>"
        )


class _ExistingFaviconHandler(BaseHandler):
    def get(self):
        self.write_html(
            '<html><head><link rel="icon" href="/mine.ico">'
            "<title>t</title></head><body>hi</body></html>"
        )


class _NoHeadHandler(BaseHandler):
    def get(self):
        self.write_html("<html><body>hi</body></html>")


class _MarkupHandler(BaseHandler):
    """Exercises the non-bytes/non-str (markupsafe.Markup) content path."""

    def get(self):
        self.write_html(
            markupsafe.Markup(
                "<html><head><title>t</title></head><body>hi</body></html>"
            )
        )


def _make_app(favicon_data_uri):
    return tornado.web.Application(
        [
            (r"/no-favicon", _NoFaviconHandler),
            (r"/existing-favicon", _ExistingFaviconHandler),
            (r"/no-head", _NoHeadHandler),
            (r"/markup", _MarkupHandler),
        ],
        favicon_data_uri=favicon_data_uri,
    )


@pytest.mark.unit
class TestWriteHtmlFaviconEnabled(tornado.testing.AsyncHTTPTestCase):
    """Favicon injection when `favicon_data_uri` is configured."""

    def get_app(self):
        return _make_app(FAVICON_URI)

    def test_injects_favicon_right_after_head_when_absent(self):
        response = self.fetch("/no-favicon")
        body = response.body.decode()

        expected_tag = (
            f'<link rel="icon" type="image/svg+xml" href="{FAVICON_URI}">'
        )
        assert expected_tag in body
        # Injected immediately after the opening <head> tag.
        assert body.index("<head>") + len("<head>") == body.index(expected_tag)

    def test_leaves_existing_favicon_untouched(self):
        response = self.fetch("/existing-favicon")
        body = response.body.decode()

        assert "/mine.ico" in body
        assert FAVICON_URI not in body
        assert body.count("<link") == 1

    def test_no_head_tag_left_unmodified(self):
        response = self.fetch("/no-head")
        assert response.body.decode() == "<html><body>hi</body></html>"

    def test_markup_content_is_injected(self):
        response = self.fetch("/markup")
        assert FAVICON_URI in response.body.decode()


@pytest.mark.unit
class TestWriteHtmlFaviconDisabled(tornado.testing.AsyncHTTPTestCase):
    """No injection should happen when no favicon is configured."""

    def get_app(self):
        return _make_app(None)

    def test_content_is_served_unmodified(self):
        response = self.fetch("/no-favicon")
        assert response.body.decode() == (
            "<html><head><title>t</title></head><body>hi</body></html>"
        )
