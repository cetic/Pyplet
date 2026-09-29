"""Executes the VFS bindings ``pyplet.client`` attaches to ``window``:
the download link and the upload pipeline, under plain CPython.
"""

import base64
from types import SimpleNamespace

import pytest

from tests import browser_stubs

_JS_NAMES = (
    "download_vfs_file",
    "upload_file",
    "handle_click",
    "handle_drop",
)


@pytest.fixture
def client_module(monkeypatch):
    yield from browser_stubs.fresh_client(monkeypatch)


@pytest.fixture
def bound(client_module, monkeypatch, tmp_path):
    """The client with its window bindings installed, jailed under tmp."""
    jail = tmp_path / "vfs_uploads"
    monkeypatch.setattr(client_module, "VFS_UPLOAD_JAIL", str(jail))
    monkeypatch.chdir(tmp_path)
    client_module._setup_vfs_bindings()
    return SimpleNamespace(
        client=client_module,
        js=client_module.js,
        window=client_module.js.window,
        document=client_module.js.document,
        console=client_module.js.console,
        jail=jail,
        root=tmp_path,
    )


def _drop_event(files):
    """A drop event shaped like the one ``pyplet.shared.dom`` emits."""
    return SimpleNamespace(
        dataTransfer=SimpleNamespace(files=browser_stubs.FakeFileList(files))
    )


def _drop(
    bound,
    files,
    client_dest=None,
    server_dest=None,
    files_limit=None,
    total_size_limit=None,
    per_file_size_limit=None,
    allowed_extensions=None,
):
    """Calls ``window.handle_drop`` with the JS argument order."""
    bound.window.handle_drop(
        _drop_event(files),
        client_dest,
        server_dest,
        files_limit,
        total_size_limit,
        per_file_size_limit,
        allowed_extensions,
    )


def _served_file(bound, relative_path, content):
    """Writes a file where ``download_vfs_file`` will look for it."""
    target = bound.root / "apps" / "proj" / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def _names_in(directory):
    return sorted(path.name for path in directory.iterdir())


class TestWindowBindings:
    def test_the_four_js_names_are_bound(self, bound):
        for name in _JS_NAMES:
            handler = getattr(bound.window, name, None)
            assert callable(handler), (
                f"window.{name} must be callable: pyplet.shared.dom emits "
                f"inline handlers calling {name}(...) by that exact name"
            )

    def test_a_second_setup_keeps_the_first_bindings(self, bound):
        first = [getattr(bound.window, name) for name in _JS_NAMES]

        bound.client._setup_vfs_bindings()

        again = [getattr(bound.window, name) for name in _JS_NAMES]
        assert again == first, (
            "_setup_vfs_bindings must no-op once window.upload_file exists, "
            "so re-bootstrapping an app cannot swap live handlers"
        )

    def test_setup_on_an_already_bound_window_is_a_no_op(self, client_module):
        client_module.js.window.upload_file = "installed by another app"

        client_module._setup_vfs_bindings()

        assert client_module.js.window.upload_file == "installed by another app"
        assert not hasattr(client_module.js.window, "handle_drop")


class TestDownload:
    def test_download_offers_the_file_as_a_base64_data_uri(self, bound):
        _served_file(bound, "data.txt", b"hello vfs")

        bound.window.download_vfs_file("data.txt")

        link = bound.document.created[-1]
        assert link.tag == "a"
        assert link.href == (
            "data:application/octet-stream;base64,"
            + base64.b64encode(b"hello vfs").decode("utf-8")
        )
        assert link.download == "data.txt"
        assert bound.document.body.appended == [link]
        assert bound.document.body.removed == [link]
        assert link.clicks == 1

    def test_download_names_the_link_after_the_leaf_only(self, bound):
        _served_file(bound, "sub/deep/report.csv", b"a,b\n")

        bound.window.download_vfs_file("sub/deep/report.csv")

        assert bound.document.created[-1].download == "report.csv"

    def test_download_of_a_missing_file_only_reports(self, bound):
        bound.window.download_vfs_file("nope.txt")

        assert len(bound.console.errors) == 1
        message = bound.console.errors[0]
        assert message.startswith("File not found: ")
        assert message.endswith("apps/proj/nope.txt")
        assert bound.document.created == []
        assert bound.document.body.appended == []

    def test_download_cannot_escape_the_served_directory(self, bound):
        bound.window.download_vfs_file("../../etc/passwd")

        message = bound.console.errors[0]
        assert message.startswith("File not found: ")
        assert message.endswith("apps/proj/etc/passwd"), (
            "the traversal scrub must keep the lookup under the app "
            f"directory, got {message!r}"
        )

    def test_download_reports_a_dom_failure_instead_of_raising(self, bound):
        _served_file(bound, "data.txt", b"hello")
        bound.document.create_error = RuntimeError("no DOM today")

        bound.window.download_vfs_file("data.txt")

        assert bound.console.errors[0].startswith("Download failed for ")
        assert "no DOM today" in bound.console.errors[0]


class TestUploadToTheVfs:
    def test_dropped_files_land_in_the_jail(self, bound):
        files = [
            browser_stubs.FakeFile("a.txt", b"aaa"),
            browser_stubs.FakeFile("b.txt", b"bbbb"),
        ]

        _drop(bound, files, client_dest="incoming")

        assert (bound.jail / "incoming" / "a.txt").read_bytes() == b"aaa"
        assert (bound.jail / "incoming" / "b.txt").read_bytes() == b"bbbb"
        assert bound.console.logs == [
            f"Uploaded to VFS: {bound.jail / 'incoming' / 'a.txt'}",
            f"Uploaded to VFS: {bound.jail / 'incoming' / 'b.txt'}",
        ]

    def test_a_nested_destination_is_created_on_the_way(self, bound):
        files = [browser_stubs.FakeFile("deep.bin", b"\x00\x01")]

        _drop(bound, files, client_dest="one/two/three")

        written = bound.jail / "one" / "two" / "three" / "deep.bin"
        assert written.read_bytes() == b"\x00\x01"

    def test_an_empty_drop_reads_nothing(self, bound):
        _drop(bound, [], client_dest="incoming")

        assert bound.window.FileReader.instances == []
        assert bound.console.errors == []

    def test_a_destination_outside_the_jail_is_denied(self, bound):
        files = [browser_stubs.FakeFile("evil.txt", b"x")]

        _drop(bound, files, client_dest="../../etc")

        assert bound.console.errors == [
            f"Access denied: Attempted to upload 'evil.txt' outside of {bound.jail}"
        ]
        assert not (bound.jail / "evil.txt").exists()
        assert not (bound.root / "etc" / "evil.txt").exists()

    def test_the_hard_size_limit_rejects_the_write(self, bound, monkeypatch):
        monkeypatch.setattr(bound.client, "MAX_UPLOAD_SIZE", 4)
        files = [browser_stubs.FakeFile("big.txt", b"12345")]

        _drop(bound, files, client_dest="incoming")

        assert bound.console.errors == [
            "Upload rejected: 'big.txt' exceeds the hard limit of 0MB."
        ]
        assert not (bound.jail / "incoming").exists()

    def test_no_destination_at_all_writes_nowhere(self, bound):
        files = [browser_stubs.FakeFile("a.txt", b"aaa")]

        _drop(bound, files)

        assert not bound.jail.exists()
        assert bound.window.fetch_calls == []
        assert bound.console.logs == []


class TestUploadLimits:
    def test_the_file_count_limit_truncates_and_warns(self, bound):
        files = [browser_stubs.FakeFile(f"f{index}.txt", b"x") for index in range(3)]

        _drop(bound, files, client_dest="in", files_limit=2)

        assert bound.console.warnings == ["Limit of 2 files exceeded. Truncating."]
        assert _names_in(bound.jail / "in") == ["f0.txt", "f1.txt"]

    def test_a_disallowed_extension_is_skipped(self, bound):
        files = [
            browser_stubs.FakeFile("keep.txt", b"ok"),
            browser_stubs.FakeFile("drop.png", b"no"),
            browser_stubs.FakeFile("noext", b"no"),
        ]

        _drop(bound, files, client_dest="in", allowed_extensions=["txt"])

        assert bound.console.errors == [
            "Skipped drop.png: Extension 'png' not allowed.",
            "Skipped noext: Extension '' not allowed.",
        ]
        assert _names_in(bound.jail / "in") == ["keep.txt"]

    def test_a_pyodide_proxy_of_extensions_is_converted_first(self, bound):
        extensions = browser_stubs.FakeJsProxy(["txt"])
        files = [
            browser_stubs.FakeFile("keep.txt", b"ok"),
            browser_stubs.FakeFile("drop.png", b"no"),
        ]

        _drop(bound, files, client_dest="in", allowed_extensions=extensions)

        assert extensions.to_py_calls == 1, (
            "a JsProxy is not iterable from Python: the filter must go "
            "through to_py() before testing membership"
        )
        assert bound.console.errors == [
            "Skipped drop.png: Extension 'png' not allowed."
        ]
        assert _names_in(bound.jail / "in") == ["keep.txt"]

    def test_the_per_file_size_limit_is_enforced(self, bound):
        files = [
            browser_stubs.FakeFile("small.txt", b"12345"),
            browser_stubs.FakeFile("large.txt", b"12345678901"),
        ]

        _drop(bound, files, client_dest="in", per_file_size_limit=10)

        assert bound.console.errors == ["Skipped large.txt: Exceeds 10 bytes."]
        assert _names_in(bound.jail / "in") == ["small.txt"]

    def test_the_total_size_budget_stops_the_second_file(self, bound):
        files = [
            browser_stubs.FakeFile("first.txt", b"123456"),
            browser_stubs.FakeFile("second.txt", b"123456"),
        ]

        _drop(bound, files, client_dest="in", total_size_limit=10)

        assert bound.console.errors == ["Skipped second.txt: Exceeds total size limit."]
        assert _names_in(bound.jail / "in") == ["first.txt"]


class TestUploadToTheServer:
    def test_the_file_is_posted_as_multipart_to_the_current_path(self, bound):
        selected = browser_stubs.FakeFile("a.txt", b"aaa")

        _drop(bound, [selected], server_dest="uploads")

        endpoint, options = bound.window.fetch_calls[0]
        assert endpoint == bound.window.location.pathname
        assert options.method == "POST"
        form = bound.window.FormData.instances[-1]
        assert options.body is form
        assert form.entries == [
            ("file", selected, "a.txt"),
            ("server_destination", "uploads"),
        ]
        assert bound.console.logs == [
            "Uploading a.txt to server destination: uploads",
            "Server upload complete: a.txt",
        ]
        assert not bound.jail.exists()

    def test_a_http_failure_is_reported(self, bound):
        bound.window.fetch_result = browser_stubs.FakePromise(
            response=SimpleNamespace(ok=False, status=507)
        )

        _drop(
            bound,
            [browser_stubs.FakeFile("a.txt", b"a")],
            server_dest="uploads",
        )

        assert bound.console.errors == ["Server upload failed for a.txt: HTTP 507"]

    def test_a_network_error_is_reported(self, bound):
        bound.window.fetch_result = browser_stubs.FakePromise(error="offline")

        _drop(
            bound,
            [browser_stubs.FakeFile("a.txt", b"a")],
            server_dest="uploads",
        )

        assert bound.console.errors == [
            "Server upload network error for a.txt: offline"
        ]

    def test_both_destinations_are_served_by_one_read(self, bound):
        _drop(
            bound,
            [browser_stubs.FakeFile("a.txt", b"aaa")],
            client_dest="in",
            server_dest="uploads",
        )

        assert (bound.jail / "in" / "a.txt").read_bytes() == b"aaa"
        assert len(bound.window.fetch_calls) == 1
        assert len(bound.window.FileReader.instances) == 1


class TestFilePicker:
    def test_the_picker_takes_several_files_and_hints_extensions(self, bound):
        bound.document.picked_files = browser_stubs.FakeFileList(
            [browser_stubs.FakeFile("a.txt", b"a")]
        )

        bound.window.upload_file(None, "in", None, None, None, None, ["txt", "csv"])

        picker = bound.document.created[-1]
        assert picker.type == "file"
        assert picker.multiple is True
        assert picker.accept == ".txt,.csv"
        assert "change" in picker.listeners
        assert picker.clicks == 1
        assert (bound.jail / "in" / "a.txt").exists()

    def test_a_single_file_limit_leaves_the_picker_single(self, bound):
        bound.window.upload_file(None, None, None, 1, None, None, None)

        picker = bound.document.created[-1]
        assert not hasattr(picker, "multiple")
        assert not hasattr(picker, "accept")

    def test_the_picker_hints_extensions_from_a_pyodide_proxy(self, bound):
        extensions = browser_stubs.FakeJsProxy(["txt"])

        bound.window.upload_file(None, None, None, None, None, None, extensions)

        assert bound.document.created[-1].accept == ".txt"

    def test_a_cancelled_picker_reads_nothing(self, bound):
        bound.window.upload_file(None, "in", None, None, None, None, None)

        assert bound.window.FileReader.instances == []
        assert not bound.jail.exists()

    def test_a_target_filename_renames_a_lone_file(self, bound):
        bound.document.picked_files = browser_stubs.FakeFileList(
            [browser_stubs.FakeFile("original.txt", b"data")]
        )

        bound.window.upload_file("renamed.txt", "in", None, None, None, None, None)

        assert (bound.jail / "in" / "renamed.txt").read_bytes() == b"data"
        assert not (bound.jail / "in" / "original.txt").exists()

    def test_a_target_filename_is_ignored_for_a_batch(self, bound):
        bound.document.picked_files = browser_stubs.FakeFileList(
            [
                browser_stubs.FakeFile("one.txt", b"1"),
                browser_stubs.FakeFile("two.txt", b"2"),
            ]
        )

        bound.window.upload_file("renamed.txt", "in", None, None, None, None, None)

        assert _names_in(bound.jail / "in") == ["one.txt", "two.txt"], (
            "an override filename must not collapse a batch onto one name"
        )

    def test_handle_click_uploads_under_the_original_names(self, bound):
        bound.document.picked_files = browser_stubs.FakeFileList(
            [browser_stubs.FakeFile("clicked.txt", b"c")]
        )

        bound.window.handle_click(None, "in", None, None, None, None, None)

        assert (bound.jail / "in" / "clicked.txt").read_bytes() == b"c"
