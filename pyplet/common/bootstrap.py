from . import dom as d
from .dom import skip, gen_id

nav = d.Node._new_factory("nav")


def navbar(*children):
    return nav(_class="navbar").append(
        d.div(_class="container").append(
            *children,
        )
    )


def input(type, *, id=skip, _class=d.auto, label=None, **props):
    if _class is d.auto:
        _class = {
            "submit": "btn btn-primary",
            "text": "form-control",
            "password": "form-control",
        }.get(type, skip)
    if id is skip and label is not None:
        id = gen_id()
    element = d.input(type=type, id=id, _class=_class, **props)
    if label is not None:
        return d.div(d.label(label, _for=id, _class="form-label"), element)
    return element


def slider(
    value=0, min=0, max=100, step=1, _class="form-range", id=skip, label=None, **props
):
    if id is skip and label is not None:
        id = gen_id()
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
