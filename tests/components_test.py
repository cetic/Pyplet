"""Unit test for pyplet components."""

from htpy import a

from pyplet.shared.dom import download


class TestComponents:
    def test_download_from_server(self):
        result = download("file.txt", "Download File")
        expected = a(
            ".primary.btn",
            href="file.txt",
            text="Download File",
            download=True,
        )
        # Compare their rendered string representations
        assert str(result) == str(expected)

    def test_download_from_vfs(self):
        result = download("file.txt", "Download File", from_vfs=True)
        expected = a(
            ".primary.btn",
            href="#",
            text="Download File",
            onclick="event.preventDefault(); download_vfs_file('file.txt');",
        )
        # Compare their rendered string representations
        assert str(result) == str(expected)
