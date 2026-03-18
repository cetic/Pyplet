"""Unit test for pyplet components."""

# import pytest
from htpy import a
from pyplet.shared.dom import download

# # Download component, is a button like component that allows
# # to download files from the client (pyscript partition) or from the server.
# def download(
#     file_path: str, button_text: str = "Download", from_vfs: bool = False
# ) -> Renderable:
#     """A download button that downloads files
#     from the client (VFS) or server.

#     Args:
#         file_path: The path to the file to download.
#         button_text: The text to display on the button.
#         from_vfs: Whether to download from the client (VFS) or server.

#     Returns:
#         A renderable element that represents the download button.
#     """

#     if from_vfs:
#         # Prevent standard link navigation and
#         # trigger frontend PyScript function
#         click_handler = (
#             f"event.preventDefault(); download_vfs_file('{file_path}');"
#         )
#         return a(
#             ".primary.btn", href="#", text=button_text, onclick=click_handler
#         )

#     # Standard server-side download
#     return a(".primary.btn", href=file_path, text=button_text, download=True)

# >>> from pyplet.shared.dom import download
# >>> print(download("file.txt", from_vfs=True))
# <a class="primary btn" href="#" text="Download" onclick="event.preventDefault(); download_vfs_file(&#39;file.txt&#39;);"></a>


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
