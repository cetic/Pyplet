"""HTPY based DOM builder and renderer.

This module provides a HTPY based DOM DSL for both
server-side HTML generation and
client-side DOM creation in Pyodide. It exposes:

Docstring style: Google.
"""

# Make all the elements available at the module level
# Ignore unused imports (multiline)

from htpy import Node  # noqa: F401
from htpy import a  # noqa: F401
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
from htpy import Element, Renderable

# from markupsafe import Markup

svg_path = Element("path")

# Components to implement:
# Download button (from server/from client)
# Upload button (to client, to server, to both)
# Graphic render (clientside, serverside)
# image (clientside/serverside)
# video/audio (clientside/serverside)
# Slider, radio, check, button (with client, server, hybrid callbacks)


# Download component, is a button like component that allows
# to download files from the client (pyscript partition) or from the server.
def download(
    file_path: str, button_text: str = "Download", from_vfs: bool = False
) -> Renderable:
    """A download button that downloads files
    from the client (VFS) or server.

    Args:
        file_path: The path to the file to download.
        button_text: The text to display on the button.
        from_vfs: Whether to download from the client (VFS) or server.

    Returns:
        A renderable element that represents the download button.
    """

    if from_vfs:
        # Prevent standard link navigation and
        # trigger frontend PyScript function
        click_handler = (
            f"event.preventDefault(); download_vfs_file('{file_path}');"
        )
        return a(
            ".primary.btn", href="#", text=button_text, onclick=click_handler
        )

    # Standard server-side download
    return a(".primary.btn", href=file_path, text=button_text, download=True)


def upload_to_client() -> Renderable:
    """An upload button that uploads files to the client."""
    ...


def upload_to_server() -> Renderable:
    """An upload button that uploads files to the server."""
    ...


def upload_to_both() -> Renderable:
    """An upload button that uploads files to both the client and server."""
    ...


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
