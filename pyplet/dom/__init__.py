"""Lightweight DOM builder and renderer.

This module provides a tiny DOM DSL for both server-side HTML generation and
client-side DOM creation in Pyodide. It exposes:

- ``Node``: a data structure representing elements,
  attributes, children and event listeners
- HTML/SVG element factories (e.g., ``div``, ``span``, ``svg``)
- ``render_html``: serialize a tree to HTML
- ``render_dom``: create live DOM nodes in the browser
- convenience helpers like ``append_class`` and ``append_style``

Docstring style: Google.
"""

import typing as T

skip = object()
auto = object()
_self_closing = {"meta", "link"}
_never_closed = {"div", "script"}


def handle_attr_kwargs(kwargs):
    return {
        (k[1:] if k.startswith("_") else k).replace("_", "-"): v
        for k, v in kwargs.items()
        if v is not skip
    }


class Node:
    """A DOM node definition.

    Args:
        tag: Tag name, e.g. ``"div"``.
        props: Sequence of key/value attributes.
        children: Sequence of strings or :class:`Node` children.
        event_listeners: Sequence of ``(event_name, handler)``
        pairs (browser-only).
        ns: Optional XML namespace (used for SVG elements).
    """

    def __init__(
        self, tag=None, *, props=(), children=(), event_listeners=(), ns=None
    ):
        self.tag = tag
        self.props = dict(props)
        self.children = list(children)
        self.event_listeners = list(event_listeners)
        self.ns = ns

    def append(self, *children, **props):
        """Append children and/or update attributes.

        Returns:
            self: to allow method chaining.
        """
        if props:
            self.props.update(handle_attr_kwargs(props))
        self.children.extend(children)
        return self

    def on(self, event_name, handler):
        """Register a browser event listener.

        Note: effective only when rendered with :func:`render_dom` in Pyodide.
        """
        self.event_listeners.append((event_name, handler))
        return self

    def append_class(self, cls):
        """Append a CSS class to the ``class`` attribute."""
        if "class" in self.props:
            cls = f"{self.props['class']} {cls}"
        self.props["class"] = cls
        return self

    def append_style(self, style):
        """Append a CSS style declaration to the ``style`` attribute."""
        if "style" in self.props:
            style = f"{self.props['style']};{style}"
        self.props["style"] = style
        return self

    @property
    def id(self):
        """Return the element ``id`` attribute if present."""
        return self.props.get("id", None)

    @property
    def classes(self):
        """Return the element ``class`` attribute if present."""
        return self.props.get("class", None)

    @staticmethod
    def _new_factory(type, ns=None):
        """Create a simple element factory for a given tag/namespace."""

        def factory(*children, **props):
            return Node(
                type,
                children=children,
                props=handle_attr_kwargs(props),
                ns=ns,
            )

        return factory

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return other is self

    def _render_dom(self, document):
        """Render this node into a live DOM Element (Pyodide only)."""
        return render_dom(self)

    def __html__(self):
        """Return HTML serialization for this node and descendants."""
        return render_html(self)


def render_html(node):
    """Serialize a node tree to HTML.

    Args:
        node: Root node to render.

    Returns:
        The HTML string.
    """

    def _render_html(node, lst):
        assert not node.event_listeners
        tag = node.tag
        lst.append(f"<{tag}")
        for k, v in node.props.items():
            lst.append(f" {k}={v!r}")
        if not node.children and tag not in _never_closed:
            lst.append(">" if tag in _self_closing else "/>")
            return
        lst.append(">")

        for child in node.children:
            if isinstance(child, str):
                lst.append(child)
            else:
                _render_html(child, lst)

        lst.append(f"</{tag}>")

    lst = [getattr(node, "prelude", "")]
    _render_html(node, lst)
    return "".join(lst)


def render_dom(node):
    """Create a live DOM Element from a node tree (browser only)."""
    from js import document

    element = (
        document.createElement(node.tag)
        if node.ns is None
        else document.createElementNS(node.ns, node.tag)
    )
    for prop, value in node.props.items():
        (
            element.setAttribute(prop, value)
            if node.ns is None
            else element.setAttributeNS(None, prop, value)
        )
    for child in node.children:
        if child is None:
            continue
        elif isinstance(child, str):
            child = document.createTextNode(child)
        else:
            child = render_dom(child)
        element.appendChild(child)
    for event_name, handler in node.event_listeners:
        element.addEventListener(event_name, handler)
    return element


def html(prelude, *children, **props):
    """Create a top-level ``<html>`` node with a prelude.

    The prelude can be used to inject a doctype or other content that must
    appear before the root element.
    """
    node = Node("html", props=handle_attr_kwargs(props), children=children)
    node.prelude = prelude
    return node


a = Node._new_factory("a")
acronym = Node._new_factory("acronym")
article = Node._new_factory("article")
aside = Node._new_factory("aside")
b = Node._new_factory("b")
body = Node._new_factory("body")
button = Node._new_factory("button")
canvas = Node._new_factory("canvas")
code = Node._new_factory("code")
details = Node._new_factory("details")
div = Node._new_factory("div")
em = Node._new_factory("em")
fieldset = Node._new_factory("fieldset")
fieldcaption = Node._new_factory("fieldcaption")
figure = Node._new_factory("figure")
form = Node._new_factory("form")
footer = Node._new_factory("footer")
h1 = Node._new_factory("h1")
h2 = Node._new_factory("h2")
h3 = Node._new_factory("h3")
h4 = Node._new_factory("h4")
h5 = Node._new_factory("h5")
h6 = Node._new_factory("h6")
head = Node._new_factory("head")
header = Node._new_factory("header")
hr = Node._new_factory("hr")
i = Node._new_factory("i")
iframe = Node._new_factory("iframe")
img = Node._new_factory("img")
input = Node._new_factory("input")
input = Node._new_factory("input")
label = Node._new_factory("label")
legend = Node._new_factory("legend")
li = Node._new_factory("li")
link = Node._new_factory("link")
meta = Node._new_factory("meta")
main = Node._new_factory("main")
nav = Node._new_factory("nav")
ol = Node._new_factory("ol")
option = Node._new_factory("option")
p = Node._new_factory("p")
pre = Node._new_factory("pre")
script = Node._new_factory("script")
section = Node._new_factory("section")
small = Node._new_factory("small")
source = Node._new_factory("source")
span = Node._new_factory("span")
strong = Node._new_factory("strong")
summary = Node._new_factory("summary")
table = Node._new_factory("table")
tbody = Node._new_factory("tbody")
select = Node._new_factory("select")
td = Node._new_factory("td")
tfoot = Node._new_factory("tfoot")
th = Node._new_factory("th")
thead = Node._new_factory("thead")
time = Node._new_factory("time")
tr = Node._new_factory("tr")
textarea = Node._new_factory("textarea")
title = Node._new_factory("title")
ul = Node._new_factory("ul")
video = Node._new_factory("video")

_SVG_NS = "http://www.w3.org/2000/svg"
circle = Node._new_factory("circle", _SVG_NS)
g = Node._new_factory("g", _SVG_NS)
image = Node._new_factory("image", _SVG_NS)
line = Node._new_factory("line", _SVG_NS)
path = Node._new_factory("path", _SVG_NS)
polygon = Node._new_factory("polygon", _SVG_NS)
rect = Node._new_factory("rect", _SVG_NS)
svg = Node._new_factory("svg", _SVG_NS)
text = Node._new_factory("text", _SVG_NS)


def append_classes(node, classes):
    """Append CSS classes to a node."""
    if "class" in node.props:
        classes = f"{node.props['class']} {classes}"
    node.props["class"] = classes


def gen_id():
    import secrets

    return f"rd-{secrets.token_hex(4)}"


P = T.ParamSpec("P")


def DomFX(f: T.Callable[T.Concatenate[Node, P], Node]) -> T.Callable[P, Node]:
    return _DomFX(f)


class _DomFX:
    def __init__(self, f, args=(), kwargs={}):
        self.f = f
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return _DomFX(self.f, args, kwargs)

    def __ror__(self, node):
        return self.f(node, *self.args, **self.kwargs)
