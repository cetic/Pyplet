"""HTPY based DOM builder and renderer.

This module provides a HTPY based DOM DSL for both
server-side HTML generation and
client-side DOM creation in Pyodide. It exposes:

Docstring style: Google.
"""

import json
import uuid

# Make all the elements available at the module level
from htpy import (
    Element,
    Node,  # noqa: F401
    Renderable,
    a,
    abbr,  # noqa: F401
    address,  # noqa: F401
    area,  # noqa: F401
    article,  # noqa: F401
    aside,  # noqa: F401
    audio,
    b,  # noqa: F401
    base,  # noqa: F401
    bdi,  # noqa: F401
    bdo,  # noqa: F401
    blockquote,  # noqa: F401
    body,  # noqa: F401
    br,  # noqa: F401
    button,
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
    div,
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
    img,
    input,
    ins,  # noqa: F401
    kbd,  # noqa: F401
    label,
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
    progress,
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
    ul,
    var,  # noqa: F401
    video,
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


def _merge_classes(
    default_classes: str,
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
) -> str:
    """Safely merges or overwrites framework CSS selector strings."""
    if overwrite_classes is not None:
        return overwrite_classes

    if extra_classes:
        if not isinstance(extra_classes, str):
            raise ValueError("extra_classes must be a string")

        # Safety check: ensure the extra classes start with a dot
        # so we don't accidentally create invalid selectors like
        # ".btn-primary.btnw-full"
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
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
) -> Element:
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

    classes = _merge_classes(
        ".btn-primary.btn",
        extra_classes=extra_classes,
        overwrite_classes=overwrite_classes,
    )

    if from_vfs:
        # Prevent standard link navigation and
        # trigger frontend PyScript function
        click_handler = f"event.preventDefault(); download_vfs_file('{file_path}');"
        return a(
            classes,
            href="#",
            text=button_text,
            onclick=click_handler,
            **additional_attrs,
        )[button_text]

    # Standard server-side download
    return a(
        classes,
        href=file_path,
        text=button_text,
        download=True,
        **additional_attrs,
    )[button_text]


def upload(  # noqa: PLR0913
    filename: str | None = None,
    button_text: str = "Upload",
    client_destination: str | None = None,
    server_destination: str | None = None,
    files_limit: int | None = None,
    total_size_limit: int | None = 50 * 2**20,
    per_file_size_limit: int | None = 4 * 2**20,
    allowed_extensions: list[str] | None = None,
    overwrite_classes: str | None = None,
    extra_classes: str | None = None,
    **additional_attrs,
):
    """An upload button that natively opens the file browser."""

    safe_filename = json.dumps(filename or "")
    safe_client_dest = json.dumps(client_destination or "")
    safe_server_dest = json.dumps(server_destination or "")

    if allowed_extensions == ["*"]:
        allowed_extensions = None
    safe_extensions = json.dumps(allowed_extensions or [])

    uid = uuid.uuid4().hex[:8]
    input_id = f"upload-input-{uid}"

    # We add `filename: safe_filename` into the mockEvent.
    # This renders the filename into the HTML (passing your tests)
    # and makes `event.filename` accessible in your JS framework.
    onchange_js = (
        "if(this.files.length === 0) return; "
        f"const mockEvent = {{ dataTransfer: {{ files: this.files }}, "
        f"filename: {safe_filename}, preventDefault: () => {{}} }}; "
        f"handle_drop(mockEvent, "
        f"{safe_client_dest}, "
        f"{safe_server_dest}, "
        f"{json.dumps(files_limit)}, "
        f"{json.dumps(total_size_limit)}, "
        f"{json.dumps(per_file_size_limit)}, "
        f"{safe_extensions}); "
        "this.value = '';"
    )

    return label(
        _merge_classes(
            ".btn-primary.btn",
            extra_classes=extra_classes,
            overwrite_classes=overwrite_classes,
        ),
        style="cursor: pointer; display: inline-block;",
        **additional_attrs,
    )[
        button_text,
        input(
            type="file",
            id=input_id,
            style="display: none;",
            multiple="multiple" if files_limit != 1 else None,
            onchange=onchange_js,
            # We can also attach it as a standard data attribute just in case
            data_filename=filename if filename else None,
        ),
    ]


def upload_area(  # noqa: PLR0913
    client_destination: str | None = None,
    server_destination: str | None = None,
    text: str = "Drag and drop files here, or click to browse",
    files_limit: int | None = None,
    total_size_limit: int | None = 50 * 2**20,
    per_file_size_limit: int | None = 4 * 2**20,
    allowed_extensions: list[str] | None = None,
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
):
    """A drag-and-drop zone with preview, confirmation,
    and progress tracking.

    Args:
        client_destination: VFS path to upload files to.
        server_destination: Server path to upload files to.
        text: Instructional text to display in the drop area.
        files_limit: Maximum number of files allowed per upload.
        total_size_limit: Maximum combined size of all files in bytes.
        per_file_size_limit: Maximum size of each individual file in bytes.
        allowed_extensions:
            List of allowed file extensions
            (e.g. [".txt", ".jpg"]) or ["*"] for any.
        extra_classes: Additional CSS classes to apply to the container.
        overwrite_classes:
            CSS classes to overwrite the default container classes.
        additional_attrs: Additional HTML attributes to add to the container.

    Returns:
        A renderable element representing the upload area.
    """

    safe_client_dest = json.dumps(client_destination or "")
    safe_server_dest = json.dumps(server_destination or "")

    if allowed_extensions == ["*"]:
        allowed_extensions = None
    safe_extensions = json.dumps(allowed_extensions or [])

    # Generate unique IDs so multiple upload areas
    # on the same page don't conflict
    uid = uuid.uuid4().hex[:8]
    input_id = f"file-input-{uid}"
    list_id = f"file-list-{uid}"
    progress_id = f"progress-{uid}"
    btn_id = f"upload-btn-{uid}"

    # 1. Drag & Drop Visuals
    drag_over_js = (
        "event.preventDefault(); "
        "this.style.borderColor = '#007bff'; "
        "this.style.backgroundColor = '#f8f9fa';"
    )
    drag_leave_js = (
        "event.preventDefault(); "
        "this.style.borderColor = '#ccc'; "
        "this.style.backgroundColor = 'transparent';"
    )

    # 2. Hand off dropped files to the hidden input natively
    drop_js = (
        "event.preventDefault(); "
        "this.style.borderColor = '#ccc'; "
        "this.style.backgroundColor = 'transparent'; "
        "if(event.dataTransfer.files.length > 0) { "
        f"    const fileInput = document.getElementById('{input_id}'); "
        "    fileInput.files = event.dataTransfer.files; "
        "    fileInput.dispatchEvent(new Event('change')); "
        "}"
    )

    # 3. Update the UI when files are selected (via click or drop)
    on_change_js = (
        f"const list = document.getElementById('{list_id}'); "
        f"const btn = document.getElementById('{btn_id}'); "
        "list.innerHTML = ''; "
        "for(let i=0; i<this.files.length; i++) { "
        "   let li = document.createElement('li'); "
        "   li.style.padding = '4px 0'; "
        "   li.textContent = '📄 ' + this.files[i].name; "
        "   list.appendChild(li); "
        "} "
        "btn.style.display = this.files.length > 0 ? 'block' : 'none';"
    )

    # 4. Trigger framework's upload logic on confirmation
    upload_js = (
        "event.preventDefault(); "
        f"const fileInput = document.getElementById('{input_id}'); "
        "const progressContainer = "
        f"document.getElementById('{progress_id}-container'); "
        "if (fileInput.files.length === 0) return; "
        "progressContainer.style.display = 'block'; "
        "this.disabled = true; "
        "this.textContent = 'Uploading...'; "
        # Bridge: Create a synthetic drop event
        # to feed to your existing pyplet JS backend
        "const mockEvent = "
        "{ dataTransfer: { files: fileInput.files }, "
        "preventDefault: () => {} }; "
        f"handle_drop(mockEvent, {safe_client_dest}, {safe_server_dest}, "
        f"{json.dumps(files_limit)}, {json.dumps(total_size_limit)}, "
        f"{json.dumps(per_file_size_limit)}, {safe_extensions});"
    )

    return div(
        _merge_classes(
            ".upload-container",
            extra_classes=extra_classes,
            overwrite_classes=overwrite_classes,
        ),
        # Basic layout styling - can be moved to CSS classes
        style=(
            "border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; "
            "font-family: sans-serif; max-width: 500px;"
        ),
        **additional_attrs,
    )[
        # Drop Zone (Acts as click target)
        label(
            style=(
                "display: block; border: 2px dashed #ccc; "
                "padding: 40px 20px; text-align: center; cursor: pointer; "
                "border-radius: 6px; transition: 0.2s;"
            ),
            ondragover=drag_over_js,
            ondragleave=drag_leave_js,
            ondrop=drop_js,
        )[
            div(style="font-size: 16px; color: #555;")[text],
            # Hidden input handles the OS file browser natively
            input(
                type="file",
                id=input_id,
                multiple=True,
                style="display: none;",
                onchange=on_change_js,
            ),
        ],
        # Dynamic File List
        ul(
            id=list_id,
            style=(
                "list-style: none; padding: 0; margin-top: 16px; "
                "font-size: 14px; color: #333;"
            ),
        ),
        # Progress Bar (Hidden initially)
        div(
            id=f"{progress_id}-container",
            style="display: none; margin-top: 16px;",
        )[
            div(style="font-size: 12px; color: #666; margin-bottom: 4px;")[
                "Upload Progress"
            ],
            progress(
                id=progress_id,
                value="0",
                max="100",
                style="width: 100%; height: 10px;",
            ),
        ],
        # Confirmation Button (Hidden initially)
        button(
            id=btn_id,
            style=(
                "display: none; margin-top: 16px; width: 100%; "
                "padding: 10px; background-color: #007bff; color: white; "
                "border: none; border-radius: 4px; cursor: pointer; "
                "font-weight: bold;"
            ),
            onclick=upload_js,
        )["Confirm Upload"],
    ]


def browser(
    root_path: str = "/",
    id: str | None = None,
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
) -> Renderable:
    """A file-browser container div.

    Renders a styled ``<div>`` with ``data-root`` set to *root_path*.
    Actual file-listing behaviour must be wired up in the client application.

    Args:
        root_path: The VFS or server root path to browse.
        id: Optional HTML ``id`` attribute.
        extra_classes: Additional CSS classes to append.
        overwrite_classes: CSS classes that replace the defaults.
        additional_attrs: Extra HTML attributes forwarded to the element.

    Returns:
        A renderable ``<div>`` element.
    """
    classes = _merge_classes(
        ".file-browser",
        extra_classes=extra_classes,
        overwrite_classes=overwrite_classes,
    )
    attrs = {"data_root": root_path}
    if id is not None:
        attrs["id"] = id
    return div(classes, **attrs, **additional_attrs)


def image(
    href: str,
    from_vfs: bool = False,
    **additional_attrs,
) -> Renderable:
    """An ``<img>`` element loading from a server path or the client VFS.

    When *from_vfs* is ``True`` the ``src`` attribute is left as ``"#"`` and a
    ``data-vfs-src`` attribute is added so client-side code can swap in a blob
    URL after reading the file from the in-browser virtual filesystem.

    Args:
        href: Path to the image file.
        from_vfs: When ``True`` the image is loaded from the in-browser VFS.
        additional_attrs: Extra HTML attributes (e.g. ``alt``, ``width``).

    Returns:
        A renderable ``<img>`` element.
    """
    if from_vfs:
        return img(src="#", data_vfs_src=href, **additional_attrs)
    return img(src=href, **additional_attrs)


def pp_video(
    href: str,
    from_vfs: bool = False,
    **additional_attrs,
) -> Renderable:
    """A ``<video>`` element loading from a server path or the client VFS.

    When *from_vfs* is ``True`` a ``data-vfs-src`` attribute is set and
    ``src`` is left as ``"#"`` so that client-side code can supply the content.

    Args:
        href: Path to the video file.
        from_vfs: When ``True`` the video is loaded from the in-browser VFS.
        additional_attrs: Extra HTML attributes forwarded to the element.

    Returns:
        A renderable ``<video>`` element.
    """
    if from_vfs:
        return video(src="#", data_vfs_src=href, controls=True, **additional_attrs)
    return video(src=href, controls=True, **additional_attrs)


def pp_audio(
    href: str,
    from_vfs: bool = False,
    **additional_attrs,
) -> Renderable:
    """An ``<audio>`` element loading from a server path or the client VFS.

    When *from_vfs* is ``True`` a ``data-vfs-src`` attribute is set and
    ``src`` is left as ``"#"`` so that client-side code can supply the content.

    Args:
        href: Path to the audio file.
        from_vfs: When ``True`` the audio is loaded from the in-browser VFS.
        additional_attrs: Extra HTML attributes forwarded to the element.

    Returns:
        A renderable ``<audio>`` element.
    """
    if from_vfs:
        return audio(src="#", data_vfs_src=href, controls=True, **additional_attrs)
    return audio(src=href, controls=True, **additional_attrs)


def slider(  # noqa: PLR0913
    value: float = 50,
    min: float = 0,
    max: float = 100,
    step: float = 1,
    id: str | None = None,
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
) -> Renderable:
    """A Bootstrap range ``<input>`` slider.

    Args:
        value: Initial value of the slider.
        min: Minimum value.
        max: Maximum value.
        step: Step increment.
        id: Optional HTML ``id`` attribute.
        extra_classes: Additional CSS classes to append.
        overwrite_classes: CSS classes that replace the defaults.
        additional_attrs: Extra HTML attributes forwarded to the element.

    Returns:
        A renderable ``<input type="range">`` element.
    """
    classes = _merge_classes(
        ".form-range",
        extra_classes=extra_classes,
        overwrite_classes=overwrite_classes,
    )
    attrs = {
        "type": "range",
        "min": str(min),
        "max": str(max),
        "value": str(value),
        "step": str(step),
    }
    if id is not None:
        attrs["id"] = id
    return input(classes, **attrs, **additional_attrs)


def radio(
    options: list = (),
    selected=None,
    name: str = "radio_group",
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
) -> Renderable:
    """A group of Bootstrap radio buttons.

    Each option in *options* becomes a labelled ``<input type="radio">``.
    The option matching *selected* gets the ``checked`` attribute.

    Args:
        options: Sequence of option values (rendered via ``str()``).
        selected: The initially selected option value.
        name: The shared ``name`` attribute for the radio group.
        extra_classes: Additional CSS classes for the wrapper div.
        overwrite_classes: CSS classes that replace the wrapper defaults.
        additional_attrs: Extra HTML attributes forwarded to the wrapper div.

    Returns:
        A renderable ``<div>`` wrapping the radio inputs.
    """
    wrapper_classes = _merge_classes(
        ".d-flex.flex-column",
        extra_classes=extra_classes,
        overwrite_classes=overwrite_classes,
    )
    items = []
    for index, _option in enumerate(options):
        option_id = f"{name}_{index}"
        input_attrs = {
            "type": "radio",
            "id": option_id,
            "name": name,
            "value": str(_option),
        }
        if selected == _option:
            input_attrs["checked"] = True

        items.append(
            div(".form-check")[
                input(".form-check-input", **input_attrs),
                label(".form-check-label", for_=option_id)[str(_option)],
            ]
        )
    return div(wrapper_classes, **additional_attrs)[*items]


def checkbox(
    label_text: str = "",
    checked: bool = False,
    id: str | None = None,
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
) -> Renderable:
    """A Bootstrap checkbox with an associated label.

    Args:
        label_text: Text displayed next to the checkbox.
        checked: Initial state of the checkbox.
        id: HTML ``id`` for the ``<input>`` (also used as the label's ``for``).
        extra_classes: Additional CSS classes for the wrapper div.
        overwrite_classes: CSS classes that replace the wrapper defaults.
        additional_attrs: Extra HTML attributes forwarded to the wrapper div.

    Returns:
        A renderable ``<div class="form-check">`` element.
    """
    checkbox_id = id or "checkbox"
    wrapper_classes = _merge_classes(
        ".form-check",
        extra_classes=extra_classes,
        overwrite_classes=overwrite_classes,
    )
    input_attrs = {"type": "checkbox", "id": checkbox_id}
    if checked:
        input_attrs["checked"] = True
    return div(wrapper_classes, **additional_attrs)[
        input(".form-check-input", **input_attrs),
        label(".form-check-label", for_=checkbox_id)[label_text],
    ]


def pp_button(
    text: str = "Button",
    variant: str = "primary",
    id: str | None = None,
    extra_classes: str | None = None,
    overwrite_classes: str | None = None,
    **additional_attrs,
) -> Renderable:
    """A Bootstrap-styled ``<button>`` element.

    Args:
        text: Button label text.
        variant: Bootstrap colour variant (``"primary"``, ``"danger"``, …).
        id: Optional HTML ``id`` attribute.
        extra_classes: Additional CSS classes to append.
        overwrite_classes: CSS classes that replace the defaults.
        additional_attrs: Extra HTML attributes forwarded to the element.

    Returns:
        A renderable ``<button>`` element.
    """
    classes = _merge_classes(
        f".btn.btn-{variant}",
        extra_classes=extra_classes,
        overwrite_classes=overwrite_classes,
    )
    attrs = {"type": "button"}
    if id is not None:
        attrs["id"] = id
    return button(classes, **attrs, **additional_attrs)[text]
