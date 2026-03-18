"""HTPY based DOM builder and renderer.

This module provides a HTPY based DOM DSL for both
server-side HTML generation and
client-side DOM creation in Pyodide. It exposes:

Docstring style: Google.
"""

# Make all the elements available at the module level
# Ignore unused imports (multiline)

from htpy import (
    Element,
    Node,  # noqa: F401
    Renderable,
    a,  # noqa: F401
    abbr,  # noqa: F401
    address,  # noqa: F401
    area,  # noqa: F401
    article,  # noqa: F401
    aside,  # noqa: F401
    audio,  # noqa: F401
    b,  # noqa: F401
    base,  # noqa: F401
    bdi,  # noqa: F401
    bdo,  # noqa: F401
    blockquote,  # noqa: F401
    body,  # noqa: F401
    br,  # noqa: F401
    button,  # noqa: F401
    canvas,  # noqa: F401
    caption,  # noqa: F401
    cite,  # noqa: F401
    code,  # noqa: F401
    col,  # noqa: F401
    colgroup,  # noqa: F401
    data,  # noqa: F401
    datalist,  # noqa: F401
    dd,  # noqa: F401
    del_,  # noqa: F401
    details,  # noqa: F401
    dfn,  # noqa: F401
    dialog,  # noqa: F401
    div,  # noqa: F401
    dl,  # noqa: F401
    dt,  # noqa: F401
    em,  # noqa: F401
    embed,  # noqa: F401
    fieldset,  # noqa: F401
    figcaption,  # noqa: F401
    figure,  # noqa: F401
    footer,  # noqa: F401
    form,  # noqa: F401
    h1,  # noqa: F401
    h2,  # noqa: F401
    h3,  # noqa: F401
    h4,  # noqa: F401
    h5,  # noqa: F401
    h6,  # noqa: F401
    head,  # noqa: F401
    header,  # noqa: F401
    hgroup,  # noqa: F401
    hr,  # noqa: F401
    html,  # noqa: F401
    i,  # noqa: F401
    iframe,  # noqa: F401
    img,  # noqa: F401
    input,  # noqa: F401
    ins,  # noqa: F401
    kbd,  # noqa: F401
    label,  # noqa: F401
    legend,  # noqa: F401
    li,  # noqa: F401
    link,  # noqa: F401
    main,  # noqa: F401
    map,  # noqa: F401
    mark,  # noqa: F401
    math,  # noqa: F401
    menu,  # noqa: F401
    meta,  # noqa: F401
    meter,  # noqa: F401
    nav,  # noqa: F401
    noscript,  # noqa: F401
    object,  # noqa: F401
    ol,  # noqa: F401
    optgroup,  # noqa: F401
    option,  # noqa: F401
    output,  # noqa: F401
    p,  # noqa: F401
    picture,  # noqa: F401
    pre,  # noqa: F401
    progress,  # noqa: F401
    q,  # noqa: F401
    rp,  # noqa: F401
    rt,  # noqa: F401
    ruby,  # noqa: F401
    s,  # noqa: F401
    samp,  # noqa: F401
    script,  # noqa: F401
    search,  # noqa: F401
    section,  # noqa: F401
    select,  # noqa: F401
    slot,  # noqa: F401
    small,  # noqa: F401
    source,  # noqa: F401
    span,  # noqa: F401
    strong,  # noqa: F401
    style,  # noqa: F401
    sub,  # noqa: F401
    summary,  # noqa: F401
    sup,  # noqa: F401
    svg,  # noqa: F401
    table,  # noqa: F401
    tbody,  # noqa: F401
    td,  # noqa: F401
    template,  # noqa: F401
    textarea,  # noqa: F401
    tfoot,  # noqa: F401
    th,  # noqa: F401
    thead,  # noqa: F401
    time,  # noqa: F401
    title,  # noqa: F401
    tr,  # noqa: F401
    track,  # noqa: F401
    u,  # noqa: F401
    ul,  # noqa: F401
    var,  # noqa: F401
    video,  # noqa: F401
    wbr,  # noqa: F401
)

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
