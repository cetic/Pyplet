from . import _dom as d


@d.DomFX
def label(node, text, row_class, col_classes=None):
    if node.id is None:
        node.append(id=d.gen_id())
    label_node = label(text, _for=node.id, _class="form-label")
    if col_classes is not None:
        a, b = col_classes.split(",")
        label_node.append_class(a)
        node = d.div(_class=b).append(node)
    return d.div(_class=row_class).append(label_node, node)


nav = d.Node._new_factory("nav")


def navbar(*children):
    return nav(_class="navbar").append(
        d.div(_class="container").append(
            *children,
        )
    )


def input(type, *, id=d.skip, _class=d.auto, label=None, **props):
    if _class is d.auto:
        _class = {
            "submit": "btn btn-primary",
            "text": "form-control",
            "password": "form-control",
        }.get(type, d.skip)
    if id is d.skip and label is not None:
        id = d.gen_id()
    element = d.input(type=type, id=id, _class=_class, **props)
    if label is not None:
        return d.div(d.label(label, _for=id, _class="form-label"), element)
    return element


def slider(
    value=0, min=0, max=100, step=1, _class="form-range", id=d.skip, label=None, **props
):
    if id is d.skip and label is not None:
        id = d.gen_id()
    slider = input(
        _class=_class,
        type="range",
        min=min,
        max=max,
        step=step,
        value=value,
        id=id,
        **props,
    )
    if label is not None:
        return d.div(d.label(label, _for=id, _class="form-label"), slider)
    return slider


def dropdown(text, btn_classes="btn btn-primary dropdown-toggle", children=()):
    # add dropdown-item class in children
    for child in children:
        if "class" not in child.props:
            child.append(_class="dropdown-item")

    node = d.div(_class="dropdown").append(
        d.button(
            text,
            _class=btn_classes,
            data_bs_toggle="dropdown",
        ),
        d.ul(_class="dropdown-menu").append(
            *[d.li(child) for child in children],
        ),
    )
    return node


def chat_header(title: str = "Chat", subtitle: str = ""):
    """Create a chat header (title + optional subtitle)."""
    if not (title or subtitle):
        return d.div()
    return d.div(_class="mb-3").append(
        d.h1(title, _class="mb-1") if title else d.span(),
        d.p(subtitle, _class="text-muted mb-0") if subtitle else d.span(),
    )


def chat_layout(
    *,
    title="Chat",
    subtitle="",
    show_header=True,
    embedded=False,
    thread_id="thread",
    empty_id="empty_state",
    empty_text="Start a conversation",
    input_id="message_input",
    send_id="send_button",
    error_id="error",
    placeholder="Message...",
    max_length=1000,
    send_label="Send",
):
    """Create a Bootstrap chat layout shell.

    Returns a Node with header, thread container, error line, and composer.
    """
    header = chat_header(title, subtitle) if show_header else None

    thread = d.div(
        _class=(
            "d-flex flex-column gap-2 flex-grow-1 overflow-auto p-3"
        ),
        id=thread_id,
    ).append(
        d.p(empty_text, _class="text-muted text-center my-auto", id=empty_id),
    )

    composer = d.div(_class="input-group").append(
        d.textarea(
            _class="form-control",
            id=input_id,
            placeholder=placeholder,
            rows="2",
            maxlength=max_length,
        ),
        d.button(send_label, _class="btn btn-primary", id=send_id, type="button"),
    )

    error = d.div(_class="text-danger small", id=error_id)

    content = d.div(_class="d-flex flex-column gap-3 flex-grow-1").append(
        thread,
        error,
        composer,
    )

    if embedded:
        if header is None:
            return content
        return d.div(_class="d-flex flex-column gap-3").append(header, content)

    items = [content]
    if header is not None:
        items.insert(0, header)
    return d.div(_class="container py-3").append(
        d.div(_class="row justify-content-center").append(
            d.div(_class="col-lg-8 d-flex flex-column gap-3").append(*items)
        )
    )


def chat_message(text, *, role="assistant", id=d.skip):
    """Create a chat message bubble node."""
    base = "px-3 py-2 rounded-3"
    if role == "user":
        classes = f"{base} align-self-end text-bg-primary"
    else:
        classes = f"{base} align-self-start bg-body-tertiary border"
    return d.div(text, _class=classes, id=id).append_style("max-width:75%")
