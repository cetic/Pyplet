"""HTPY based DOM builder and renderer.

This module provides a HTPY based DOM DSL for both
server-side HTML generation and
client-side DOM creation in Pyodide. It exposes:

Docstring style: Google.
"""

import json
from typing import Optional

# Make all the elements available at the module level
from htpy import Node  # noqa: F401
from htpy import abbr  # noqa: F401
from htpy import address  # noqa: F401
from htpy import area  # noqa: F401
from htpy import article  # noqa: F401
from htpy import aside  # noqa: F401
from htpy import audio  # noqa: F401
from htpy import b  # noqa: F401
from htpy import base  # noqa: F401
from htpy import bdi  # noqa: F401
from htpy import bdo  # noqa: F401
from htpy import blockquote  # noqa: F401
from htpy import body  # noqa: F401
from htpy import br  # noqa: F401
from htpy import button  # noqa: F401
from htpy import canvas  # noqa: F401
from htpy import caption  # noqa: F401
from htpy import cite  # noqa: F401
from htpy import code  # noqa: F401
from htpy import col  # noqa: F401
from htpy import colgroup  # noqa: F401
from htpy import data  # noqa: F401
from htpy import datalist  # noqa: F401
from htpy import dd  # noqa: F401
from htpy import del_  # noqa: F401
from htpy import details  # noqa: F401
from htpy import dfn  # noqa: F401
from htpy import dialog  # noqa: F401
from htpy import div  # noqa: F401
from htpy import dl  # noqa: F401
from htpy import dt  # noqa: F401
from htpy import em  # noqa: F401
from htpy import embed  # noqa: F401
from htpy import fieldset  # noqa: F401
from htpy import figcaption  # noqa: F401
from htpy import figure  # noqa: F401
from htpy import footer  # noqa: F401
from htpy import form  # noqa: F401
from htpy import h1  # noqa: F401
from htpy import h2  # noqa: F401
from htpy import h3  # noqa: F401
from htpy import h4  # noqa: F401
from htpy import h5  # noqa: F401
from htpy import h6  # noqa: F401
from htpy import head  # noqa: F401
from htpy import header  # noqa: F401
from htpy import hgroup  # noqa: F401
from htpy import hr  # noqa: F401
from htpy import html  # noqa: F401
from htpy import i  # noqa: F401
from htpy import iframe  # noqa: F401
from htpy import img  # noqa: F401
from htpy import input  # noqa: F401
from htpy import ins  # noqa: F401
from htpy import kbd  # noqa: F401
from htpy import label  # noqa: F401
from htpy import legend  # noqa: F401
from htpy import li  # noqa: F401
from htpy import link  # noqa: F401
from htpy import main  # noqa: F401
from htpy import map  # noqa: F401
from htpy import mark  # noqa: F401
from htpy import math  # noqa: F401
from htpy import menu  # noqa: F401
from htpy import meta  # noqa: F401
from htpy import meter  # noqa: F401
from htpy import nav  # noqa: F401
from htpy import noscript  # noqa: F401
from htpy import object  # noqa: F401
from htpy import ol  # noqa: F401
from htpy import optgroup  # noqa: F401
from htpy import option  # noqa: F401
from htpy import output  # noqa: F401
from htpy import p  # noqa: F401
from htpy import picture  # noqa: F401
from htpy import pre  # noqa: F401
from htpy import progress  # noqa: F401
from htpy import q  # noqa: F401
from htpy import rp  # noqa: F401
from htpy import rt  # noqa: F401
from htpy import ruby  # noqa: F401
from htpy import s  # noqa: F401
from htpy import samp  # noqa: F401
from htpy import script  # noqa: F401
from htpy import search  # noqa: F401
from htpy import section  # noqa: F401
from htpy import select  # noqa: F401
from htpy import slot  # noqa: F401
from htpy import small  # noqa: F401
from htpy import source  # noqa: F401
from htpy import span  # noqa: F401
from htpy import strong  # noqa: F401
from htpy import style  # noqa: F401
from htpy import sub  # noqa: F401
from htpy import summary  # noqa: F401
from htpy import sup  # noqa: F401
from htpy import svg  # noqa: F401
from htpy import table  # noqa: F401
from htpy import tbody  # noqa: F401
from htpy import td  # noqa: F401
from htpy import template  # noqa: F401
from htpy import textarea  # noqa: F401
from htpy import tfoot  # noqa: F401
from htpy import th  # noqa: F401
from htpy import thead  # noqa: F401
from htpy import time  # noqa: F401
from htpy import title  # noqa: F401
from htpy import tr  # noqa: F401
from htpy import track  # noqa: F401
from htpy import u  # noqa: F401
from htpy import ul  # noqa: F401
from htpy import var  # noqa: F401
from htpy import video  # noqa: F401
from htpy import wbr  # noqa: F401
from htpy import Element, Renderable, a

# from markupsafe import Markup

svg_path = Element("path")

# Components to implement:
# Download button (from server/from client)
# Upload button (to client, to server, to both)
# Graphic render (clientside, serverside)
# image (clientside/serverside)
# video/audio (clientside/serverside)
# Slider, radio, check, button (with client, server, hybrid callbacks)


def _merge_classes(
    default_classes: str,
    extra_classes: Optional[str] = None,
    overwrite_classes: Optional[str] = None,
) -> str:
    """Safely merges or overwrites framework CSS selector strings."""
    if overwrite_classes is not None:
        return overwrite_classes

    if extra_classes:
        if not isinstance(extra_classes, str):
            raise ValueError("extra_classes must be a string")

        # Safety check: ensure the extra classes start with a dot
        # so we don't accidentally create invalid selectors like
        # ".primary.btnw-full"
        if not extra_classes.startswith("."):
            extra_classes = "." + extra_classes.replace(" ", ".")

        return f"{default_classes}{extra_classes}"

    return default_classes


# Download component, is a button like component that allows
# to download files from the client (pyscript partition) or from the server.
def download(
    file_path: str,
    button_text: str = "Download",
    from_vfs: bool = False,
    extra_classes: Optional[str] = None,
    overwrite_classes: Optional[str] = None,
    **additional_attrs,
) -> Renderable:
    """A download button that downloads files
    from the client (VFS) or server.

    Args:
        file_path: The path to the file to download.
        button_text: The text to display on the button.
        from_vfs: Whether to download from the client (VFS) or server.
        extra_classes: Additional CSS classes to apply to the button.
        overwrite_classes: CSS classes to overwrite the default classes.
        additional_attrs: Additional attributes to add to the button.

    Returns:
        A renderable element that represents the download button.
    """

    classes = _merge_classes(".primary.btn", overwrite_classes, extra_classes)

    if from_vfs:
        # Prevent standard link navigation and
        # trigger frontend PyScript function
        click_handler = (
            f"event.preventDefault(); download_vfs_file('{file_path}');"
        )
        return a(
            classes,
            href="#",
            text=button_text,
            onclick=click_handler,
            **additional_attrs,
        )

    # Standard server-side download
    return a(
        classes,
        href=file_path,
        text=button_text,
        download=True,
        **additional_attrs,
    )


def upload(
    filename: Optional[str] = None,
    button_text: str = "Upload",
    client_destination: Optional[str] = None,
    server_destination: Optional[str] = None,
    files_limit: Optional[int] = None,
    total_size_limit: Optional[int] = 50 * 2**20,
    per_file_size_limit: Optional[int] = 4 * 2**20,
    allowed_extensions: Optional[list[str]] = None,
    overwrite_classes: Optional[str] = None,
    extra_classes: Optional[str] = None,
    **additional_attrs,
) -> Renderable:
    """An upload button that uploads files to the client (VFS) and/or server.

    Args:
        filename: The name of the file to upload.
        button_text: The text to display on the button.
        client_destination: The path to the client (VFS) destination.
        server_destination: The path to the server destination.
        files_limit: The maximum number of files to upload.
        total_size_limit: The maximum total size of all uploaded files.
        per_file_size_limit: The maximum size of each uploaded file.
        allowed_extensions: A list of allowed file extensions
        (e.g. ["jpg", "png"], ["*"]).
        overwrite_classes: A string of classes to overwrite
        the default classes.
        extra_classes: A string of classes to add to the button.
        additional_attrs: Additional attributes to add to the button.

    Returns:
        A renderable element that represents the upload button.
    """

    # json.dumps safely formats strings and turns None into null for JavaScript
    safe_filename = json.dumps(filename or "")
    safe_client_dest = json.dumps(client_destination or "")
    safe_server_dest = json.dumps(server_destination or "")

    if allowed_extensions == ["*"]:
        allowed_extensions = None

    onclick_js = (
        "event.preventDefault(); "
        "upload_file("
        f"{safe_filename}, "
        f"{safe_client_dest}, "
        f"{safe_server_dest}, "
        f"{files_limit}, "
        f"{total_size_limit}, "
        f"{per_file_size_limit}, "
        f"{json.dumps(allowed_extensions or [])});"
    )

    return a(
        _merge_classes(
            "primary btn",
            extra_classes=extra_classes,
            overwrite_classes=overwrite_classes,
        ),
        href="#",
        text=button_text,
        onclick=onclick_js,
        **additional_attrs,
    )


def upload_area(
    client_destination: Optional[str] = None,
    server_destination: Optional[str] = None,
    text: str = "Drag and drop files here",
    files_limit: Optional[int] = None,
    total_size_limit: Optional[int] = 50 * 2**20,
    per_file_size_limit: Optional[int] = 4 * 2**20,
    allowed_extensions: Optional[list[str]] = None,
    extra_classes: Optional[str] = None,
    overwrite_classes: Optional[str] = None,
    **additional_attrs,
) -> Renderable:
    """A drag-and-drop zone for uploading files
    to the client (VFS) and/or server.

    Args:
        client_destination: The VFS path to upload files to.
        server_destination: The server path to upload files to.
        text: The text to display in the upload area.
        files_limit: The maximum number of files to upload.
        total_size_limit: The maximum total size of all files to upload.
        per_file_size_limit: The maximum size of each file to upload.
        allowed_extensions: A list of allowed file extensions.
        extra_classes: Additional CSS classes to apply to the upload area.
        overwrite_classes: CSS classes to overwrite the default classes.
        additional_attrs: Additional attributes to add to the upload area.

    Returns:
        A renderable div element representing the upload area.
    """

    safe_client_dest = json.dumps(client_destination or "")
    safe_server_dest = json.dumps(server_destination or "")

    # JS handlers to manage the visual state and
    # prevent default browser navigation
    drag_over_js = "event.preventDefault(); this.classList.add('drag-over');"
    drag_leave_js = (
        "event.preventDefault(); this.classList.remove('drag-over');"
    )

    if allowed_extensions == ["*"]:
        allowed_extensions = None

    # On drop, prevent navigation, reset visual state, and hand off to Python
    drop_js = (
        "event.preventDefault(); "
        "this.classList.remove('drag-over'); "
        "handle_drop(event, "
        f"{safe_client_dest}, "
        f"{safe_server_dest}, "
        f"{files_limit}, "
        f"{total_size_limit}, "
        f"{per_file_size_limit}, "
        f"{json.dumps(allowed_extensions or [])});"
    )

    # On click, open the file picker
    click_js = (
        "event.preventDefault(); "
        "this.classList.remove('drag-over'); "
        "handle_click(event, "
        f"{safe_client_dest}, "
        f"{safe_server_dest}, "
        f"{files_limit}, "
        f"{total_size_limit}, "
        f"{per_file_size_limit}, "
        f"{json.dumps(allowed_extensions or [])});"
    )

    return div(
        _merge_classes(
            "upload-area",
            extra_classes=extra_classes,
            overwrite_classes=overwrite_classes,
        ),
        text=text,
        ondragover=drag_over_js,
        ondragleave=drag_leave_js,
        ondrop=drop_js,
        onclick=click_js,
        **additional_attrs,
    )


def render_graphic_on_client() -> Renderable:
    """A button that renders graphics on the client."""
    ...


def render_graphic_on_server() -> Renderable:
    """A button that renders graphics on the server."""
    ...


def image_from_client() -> Renderable:
    """An image that is rendered on the client."""
    ...


def image_from_server() -> Renderable:
    """An image that is rendered on the server."""
    ...


def video_from_client() -> Renderable:
    """A video that is rendered on the client."""
    ...


def video_from_server() -> Renderable:
    """A video that is rendered on the server."""
    ...


def audio_from_client() -> Renderable:
    """An audio that is rendered on the client."""
    ...


def audio_from_server() -> Renderable:
    """An audio that is rendered on the server."""
    ...


def slider_with_client_callbacks() -> Renderable:
    """A slider that is controlled on the client."""
    ...


def slider_with_server_callbacks() -> Renderable:
    """A slider that is controlled on the server."""
    ...


def slider_with_server_and_client_callbacks() -> Renderable:
    """A slider that is controlled on both the client and server."""
    ...


def radio_button_with_client_callbacks() -> Renderable:
    """A radio button that is controlled on the client."""
    ...


def radio_button_with_server_callbacks() -> Renderable:
    """A radio button that is controlled on the server."""
    ...


def radio_button_with_server_and_client_callbacks() -> Renderable:
    """A radio button that is controlled on both the client and server."""
    ...


def checkbox_with_client_callbacks() -> Renderable:
    """A checkbox that is controlled on the client."""
    ...


def checkbox_with_server_callbacks() -> Renderable:
    """A checkbox that is controlled on the server."""
    ...


def checkbox_with_server_and_client_callbacks() -> Renderable:
    """A checkbox that is controlled on both the client and server."""
    ...


def button_with_client_callbacks() -> Renderable:
    """A button that is controlled on the client."""
    ...


def button_with_server_callbacks() -> Renderable:
    """A button that is controlled on the server."""
    ...


def button_with_server_and_client_callbacks() -> Renderable:
    """A button that is controlled on both the client and server."""
    ...
