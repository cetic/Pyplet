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
from htpy import Renderable

# Components to implement:
# Download button (from server/from client)
# Upload button (to client, to server, to both)
# Graphic render (clientside, serverside)
# image (clientside/serverside)
# video/audio (clientside/serverside)
# Slider, radio, check, button (with client, server, hybrid callbacks)


def download_from_client() -> Renderable:
    """A download button that downloads files from the client."""
    ...


def download_from_server() -> Renderable:
    """A download button that downloads files from the server."""
    ...


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


# import typing as T

# skip = object()
# auto = object()
# _self_closing = {"meta", "link"}
# _never_closed = {"div", "script"}


# def handle_attr_kwargs(kwargs):
#     return {
#         (k[1:] if k.startswith("_") else k).replace("_", "-"): v
#         for k, v in kwargs.items()
#         if v is not skip
#     }


# class Node:
#     """A DOM node definition.

#     Args:
#         tag: Tag name, e.g. ``"div"``.
#         props: Sequence of key/value attributes.
#         children: Sequence of strings or :class:`Node` children.
#         event_listeners: Sequence of ``(event_name, handler)``
#         pairs (browser-only).
#         ns: Optional XML namespace (used for SVG elements).
#     """

#     def __init__(
#         self, tag=None, *, props=(), children=(), event_listeners=(), ns=None
#     ):
#         self.tag = tag
#         self.props = dict(props)
#         self.children = list(children)
#         self.event_listeners = list(event_listeners)
#         self.ns = ns

#     def append(self, *children, **props):
#         """Append children and/or update attributes.

#         Returns:
#             self: to allow method chaining.
#         """
#         if props:
#             self.props.update(handle_attr_kwargs(props))
#         self.children.extend(children)
#         return self

#     def on(self, event_name, handler):
#         """Register a browser event listener.

#         Note: effective only when rendered with
# :func:`render_dom` in Pyodide.
#         """
#         self.event_listeners.append((event_name, handler))
#         return self

#     def append_class(self, cls):
#         """Append a CSS class to the ``class`` attribute."""
#         if "class" in self.props:
#             cls = f"{self.props['class']} {cls}"
#         self.props["class"] = cls
#         return self

#     def append_style(self, style):
#         """Append a CSS style declaration to the ``style`` attribute."""
#         if "style" in self.props:
#             style = f"{self.props['style']};{style}"
#         self.props["style"] = style
#         return self

#     @property
#     def id(self):
#         """Return the element ``id`` attribute if present."""
#         return self.props.get("id", None)

#     @property
#     def classes(self):
#         """Return the element ``class`` attribute if present."""
#         return self.props.get("class", None)

#     @staticmethod
#     def _new_factory(type, ns=None):
#         """Create a simple element factory for a given tag/namespace."""

#         def factory(*children, **props):
#             return Node(
#                 type,
#                 children=children,
#                 props=handle_attr_kwargs(props),
#                 ns=ns,
#             )

#         return factory

#     def __hash__(self):
#         return id(self)

#     def __eq__(self, other):
#         return other is self

#     def _render_dom(self, document):
#         """Render this node into a live DOM Element (Pyodide only)."""
#         return render_dom(self)

#     def __html__(self):
#         """Return HTML serialization for this node and descendants."""
#         return render_html(self)


# def render_html(node):
#     """Serialize a node tree to HTML.

#     Args:
#         node: Root node to render.

#     Returns:
#         The HTML string.
#     """

#     def _render_html(node, lst):
#         assert not node.event_listeners
#         tag = node.tag
#         lst.append(f"<{tag}")
#         for k, v in node.props.items():
#             lst.append(f" {k}={v!r}")
#         if not node.children and tag not in _never_closed:
#             lst.append(">" if tag in _self_closing else "/>")
#             return
#         lst.append(">")

#         for child in node.children:
#             if isinstance(child, str):
#                 lst.append(child)
#             else:
#                 _render_html(child, lst)

#         lst.append(f"</{tag}>")

#     lst = [getattr(node, "prelude", "")]
#     _render_html(node, lst)
#     return "".join(lst)


# def render_dom(node):
#     """Create a live DOM Element from a node tree (browser only)."""
#     from js import document

#     element = (
#         document.createElement(node.tag)
#         if node.ns is None
#         else document.createElementNS(node.ns, node.tag)
#     )
#     for prop, value in node.props.items():
#         (
#             element.setAttribute(prop, value)
#             if node.ns is None
#             else element.setAttributeNS(None, prop, value)
#         )
#     for child in node.children:
#         if child is None:
#             continue
#         elif isinstance(child, str):
#             child = document.createTextNode(child)
#         else:
#             child = render_dom(child)
#         element.appendChild(child)
#     for event_name, handler in node.event_listeners:
#         element.addEventListener(event_name, handler)
#     return element


# def html(prelude, *children, **props):
#     """Create a top-level ``<html>`` node with a prelude.

#     The prelude can be used to inject a doctype or other content that must
#     appear before the root element.
#     """
#     node = Node("html", props=handle_attr_kwargs(props), children=children)
#     node.prelude = prelude
#     return node


# a = Node._new_factory("a")
# acronym = Node._new_factory("acronym")
# article = Node._new_factory("article")
# aside = Node._new_factory("aside")
# b = Node._new_factory("b")
# body = Node._new_factory("body")
# button = Node._new_factory("button")
# canvas = Node._new_factory("canvas")
# code = Node._new_factory("code")
# details = Node._new_factory("details")
# div = Node._new_factory("div")
# em = Node._new_factory("em")
# fieldset = Node._new_factory("fieldset")
# fieldcaption = Node._new_factory("fieldcaption")
# figure = Node._new_factory("figure")
# form = Node._new_factory("form")
# footer = Node._new_factory("footer")
# h1 = Node._new_factory("h1")
# h2 = Node._new_factory("h2")
# h3 = Node._new_factory("h3")
# h4 = Node._new_factory("h4")
# h5 = Node._new_factory("h5")
# h6 = Node._new_factory("h6")
# head = Node._new_factory("head")
# header = Node._new_factory("header")
# hr = Node._new_factory("hr")
# i = Node._new_factory("i")
# iframe = Node._new_factory("iframe")
# img = Node._new_factory("img")
# input = Node._new_factory("input")
# input = Node._new_factory("input")
# label = Node._new_factory("label")
# legend = Node._new_factory("legend")
# li = Node._new_factory("li")
# link = Node._new_factory("link")
# meta = Node._new_factory("meta")
# main = Node._new_factory("main")
# nav = Node._new_factory("nav")
# ol = Node._new_factory("ol")
# option = Node._new_factory("option")
# p = Node._new_factory("p")
# pre = Node._new_factory("pre")
# script = Node._new_factory("script")
# section = Node._new_factory("section")
# small = Node._new_factory("small")
# source = Node._new_factory("source")
# span = Node._new_factory("span")
# strong = Node._new_factory("strong")
# summary = Node._new_factory("summary")
# table = Node._new_factory("table")
# tbody = Node._new_factory("tbody")
# select = Node._new_factory("select")
# td = Node._new_factory("td")
# tfoot = Node._new_factory("tfoot")
# th = Node._new_factory("th")
# thead = Node._new_factory("thead")
# time = Node._new_factory("time")
# tr = Node._new_factory("tr")
# textarea = Node._new_factory("textarea")
# title = Node._new_factory("title")
# ul = Node._new_factory("ul")
# video = Node._new_factory("video")

# _SVG_NS = "http://www.w3.org/2000/svg"
# circle = Node._new_factory("circle", _SVG_NS)
# g = Node._new_factory("g", _SVG_NS)
# image = Node._new_factory("image", _SVG_NS)
# line = Node._new_factory("line", _SVG_NS)
# path = Node._new_factory("path", _SVG_NS)
# polygon = Node._new_factory("polygon", _SVG_NS)
# rect = Node._new_factory("rect", _SVG_NS)
# svg = Node._new_factory("svg", _SVG_NS)
# text = Node._new_factory("text", _SVG_NS)


# def append_classes(node, classes):
#     """Append CSS classes to a node."""
#     if "class" in node.props:
#         classes = f"{node.props['class']} {classes}"
#     node.props["class"] = classes


# def gen_id():
#     import secrets

#     return f"rd-{secrets.token_hex(4)}"


# P = T.ParamSpec("P")


# def DomFX(f: T.Callable[T.Concatenate[Node, P],
#  Node]) -> T.Callable[P, Node]:
#     return _DomFX(f)


# class _DomFX:
#     def __init__(self, f, args=(), kwargs={}):
#         self.f = f
#         self.args = args
#         self.kwargs = kwargs

#     def __call__(self, *args, **kwargs):
#         return _DomFX(self.f, args, kwargs)

#     def __ror__(self, node):
#         return self.f(node, *self.args, **self.kwargs)
