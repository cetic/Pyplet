import datetime
import glob
from typing import Optional

from tornado.web import RequestHandler

from ..dom import (
    Node,
    a,
    body,
    div,
    footer,
    head,
    html,
    li,
    link,
    main,
    meta,
    nav,
    p,
    script,
    span,
    title,
    ul,
)
from . import config

current_year = datetime.datetime.now().year


def base_template(
    *,
    page_title: Optional[str] = None,
    navbar: Node,
    content: list | Node,
    additional_head_node: Optional[Node] = None,
    contain_in: str | None = "container mt-2",
    page_footer: bool = True,
):
    """Base template for Pyplet web pages.

    Args:
        page_title (str): Page title.
        navbar (Node): Navbar content.
        content (Node): Page content.
        additional_head_node (Node): Additional head elements.
        contain_in (str): Container class.
        page_footer (bool): Whether to show the footer.
    """
    if not isinstance(content, list):
        content = [content]

    if contain_in is not None:
        content = [div(f".{contain_in.replace(' ', '.')}")[*content]]

    return html(".h-100", lang="en")[
        head[
            meta(charset="utf-8"),
            meta(
                name="viewport", content="width=device-width, initial-scale=1"
            ),
            title[f"{page_title} - Pyplet" if page_title else "Pyplet"],
            link(
                href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",  # noqa: E501
                rel="stylesheet",
                integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH",  # noqa: E501
                crossorigin="anonymous",
            ),
            additional_head_node,
        ],
        body(".d-flex.flex-column.h-100")[
            main(".flex-fill")[
                navbar,
                *content,
            ],
            (
                footer(".footer.mt-auto.py-3.bg-light")[
                    div(".container")[
                        span(".text-muted")[
                            "© Copyright CETIC 2024 - "
                            f"{current_year}. All rights reserved",
                        ]
                    ]
                ]
                if page_footer
                else footer(".footer.mt-auto")
            ),
            script(
                src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",  # noqa: E501
                integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz",  # noqa: E501
                crossorigin="anonymous",
            ),
        ],
    ]


def default_navbar(handler: RequestHandler) -> Node:
    """Default navbar for Pyplet web pages.

    Args:
        handler (RequestHandler): Request handler.

    Returns:
        Node: Navbar content.
    """
    return nav(".navbar.navbar-expand-sm.bg-body-tertiary")[
        div(".container")[
            # Brand
            a(".navbar-brand", href="/")["Pyplet"],
            # Right menu
            ul(".navbar-nav.ms-auto")[
                # About
                li(".nav-item")[
                    a(".nav-link", href="/about")["About Pyplet"],
                ],
            ],
        ]
    ]


def index_template(handler: RequestHandler) -> Node:
    """Index template for Pyplet web pages.

    Args:
        handler (RequestHandler): Request handler.

    Returns:
        Node: Index content.
    """

    # Rewrite using htpy components
    applications = sorted(
        [
            (paragraph[:-10].split("/")[0], paragraph[:-10].split("/")[1])
            for paragraph in sorted(
                glob.glob("*/*_client.py", root_dir=config.apps)
            )
        ]
    )

    complete_tree = ul[
        *[
            li[
                app_name,
                ul[
                    *[
                        li[
                            a(href=f"apps/{project}/{app_name}")[
                                app_subname.removesuffix("_client.py").split(
                                    "/"
                                )[-1]
                            ]
                        ]
                        for app_subname in glob.glob(
                            f"{project}/*_client.py", root_dir=config.apps
                        )
                    ]
                ],
            ]
            for project, app_name in applications
        ]
    ]

    return base_template(
        page_title="Index",
        navbar=default_navbar(handler),
        content=[
            p["Welcome to Pyplet!"],
            p["The following applications are available:"],
            complete_tree,
        ],
    )


def about_template(handler: RequestHandler) -> Node:
    """About template for Pyplet web pages.

    Args:
        handler (RequestHandler): Request handler.

    Returns:
        Node: About content.
    """
    return base_template(
        page_title="About",
        navbar=default_navbar(handler),
        content=[
            div(".col-sm-8.mx-auto")[
                p["Pyplet is a full-Python application server."],
                p[
                    "It is developed at the ",
                    a(href="https://www.cetic.be/", target="_blank")["CETIC"],
                    " to develop web applications.",
                ],
                p[
                    "Its applications can be written entirely in Python while"
                    " leveraging two of the most vibrant programming "
                    "communities in the world: the JavaScript and Python "
                    "ecosystems."
                ],
            ]
        ],
    )


def application_template(
    title: str, handler: "RequestHandler", content: dict | Node | list
) -> Node:
    """Returns the application template for the given title and content.

    Args:
        title (str): The title of the page.
        handler (RequestHandler): The request handler.
        content (dict | Node | list): A dictionary with 'head' and
                                      'body' keys, or a standard
                                      Node/list of Nodes for the body.

    Returns:
        Node: The application template.
    """
    additional_head = []
    body_content = []
    kwargs = {}

    # 1. Handle the new dictionary structure
    if isinstance(content, dict):
        additional_head = content.get("head", [])
        body_content = content.get("body", [])

        # Mirroring your previous logic:
        # if there's explicit body content defined
        # this way, adjust the container kwargs
        if body_content:
            kwargs["contain_in"] = None

    # 2. Handle a standard htpy Node or a list of Nodes
    else:
        if isinstance(content, list):
            body_content = content
        else:
            body_content = [content]

    return base_template(
        page_title=title,
        navbar=default_navbar(handler),
        content=body_content,
        additional_head_node=additional_head,
        page_footer=False,
        **kwargs,
    )
