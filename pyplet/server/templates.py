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
    additional_head=(),
    contain_in: str | None = "container mt-2",
    page_footer: bool = True,
):
    """Base template for Pyplet web pages.

    Args:
        title (str): Page title.
        navbar (Node): Navbar content.
        content (Node): Page content.
        additional_head (tuple): Additional head elements.
        contain_in (str): Container class.
        footer (bool): Whether to show the footer.
    """
    if not isinstance(content, list):
        content = [content]

    if contain_in is not None:
        content = [div(f".{contain_in.replace(' ', '.')}")[*content]]

    # return d.html("<!doctype html>", lang="en", _class="h-100").append(
    #     d.head(
    #         d.meta(charset="utf-8"),
    #         d.meta(
    #             name="viewport",
    # content="width=device-width, initial-scale=1"
    #         ),
    #         d.title(f"{title} - Pyplet" if title else "Pyplet"),
    #         d.link(
    #             href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",  # noqa: E501
    #             rel="stylesheet",
    #             integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH",  # noqa: E501
    #             crossorigin="anonymous",
    #         ),
    #         *additional_head,
    #     ),
    #     d.body(_class="d-flex flex-column h-100").append(
    #         d.main(_class="flex-fill").append(
    #             navbar,
    #             *content,
    #         ),
    #         (
    #             d.footer(_class="footer mt-auto py-3 bg-light").append(
    #                 d.div(_class="container").append(
    #                     d.span(_class="text-muted").append(
    #                         "&copy; Copyright CETIC 2024 - "
    #                         f"{current_year}. All rights reserved",
    #                     )
    #                 )
    #             )
    #             if footer
    #             else d.footer(_class="footer mt-auto")
    #         ),
    #         d.script(
    #             src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",  # noqa: E501
    #             integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz",  # noqa: E501
    #             crossorigin="anonymous",
    #         ),
    #     ),
    # )

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
            *additional_head,
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
    # return d.nav(_class="navbar navbar-expand-sm bg-body-tertiary").append(
    #     d.div(_class="container").append(
    #         # Brand
    #         d.a("Pyplet", _class="navbar-brand", href="/"),
    #         # Right menu
    #         d.ul(_class="navbar-nav ms-auto").append(
    #             # About
    #             d.li(_class="nav-item").append(
    #                 d.a("About Pyplet", href="/about", _class="nav-link"),
    #             ),
    #         ),
    #     )
    # )
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
    # applications = [
    #     "/" + paragraph[:-10]
    #     for paragraph in sorted(
    #         glob.glob("*/*_client.py", root_dir=config.apps)
    #     )
    # ]
    # projects = collections.defaultdict(ul)
    # for application in applications:
    #     project, app_name = application.split("/")[-2:]
    #     projects[project].append(
    #         li[a(href=f"apps/{project}/{app_name}")[app_name]]
    #     )
    # application_list = ul[
    #     *[
    #         li[a(href=f"apps/{project}/{app_name}")[app_name]]
    #         for project, apps in projects.items()
    #     ]
    # ]

    # Rewrite using htpy components
    applications = sorted(
        [
            (paragraph[:-10].split("/")[0], paragraph[:-10].split("/")[1])
            for paragraph in sorted(
                glob.glob("*/*_client.py", root_dir=config.apps)
            )
        ]
    )

    # Build the project/apps tree
    complete_tree = ul[
        *[
            li[a(href=f"apps/{project}/{app_name}")[app_name]]
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
            # d.div(_class="col-sm-8 mx-auto").append(
            #     d.p("Pyplet is a full-Python application server."),
            #     d.p(
            #         "It is developed at the ",
            #         d.a(
            #             "CETIC", href="https://www.cetic.be/",
            #  target="_blank"
            #         ),
            #         " to develop web applications.",
            #     ),
            #     d.p(
            #         "Its applications can be written
            #  entirely in Python while"
            #         " leveraging two of the most vibrant programming "
            #         "communities in the world: the JavaScript and Python "
            #         "ecosystems."
            #     ),
            # ),
            # Rewrite using htpy
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
    title: str, handler: RequestHandler, content: Node | list
) -> Node:
    """Returns the application template for the given title and content.

    Args:
        title (str): The title of the page.
        handler (RequestHandler): The request handler.
        content (d.Node | list): The content of the page.

    Returns:
        Node: The application template.
    """
    additional_head = ()
    kwargs = {}
    if content and getattr(content[0], "tag", None) == "head":
        additional_head = content[0].children
        content = content[1:]

    if content and getattr(content[0], "tag", None) == "body":
        kwargs["contain_in"] = None
        content = content[0].children

    return base_template(
        page_title=title,
        navbar=default_navbar(handler),
        content=content,
        additional_head=additional_head,
        page_footer=False,
        **kwargs,
    )
