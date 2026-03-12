import collections
import datetime
import glob
from typing import Optional

from tornado.web import RequestHandler

from ..shared.dom import (
    Node,
    a,
    body,
    button,
    div,
    em,
    footer,
    form,
    h4,
    head,
    hr,
    html,
    input,
    label,
    li,
    link,
    main,
    meta,
    nav,
    p,
    script,
    span,
    strong,
    svg,
    svg_path,
    title,
    ul,
)
from . import config, magiclink, oauth

current_year = datetime.datetime.now().year


def base_template(
    *,
    page_title: Optional[str] = None,
    navbar: Node,
    content: list | Node,
    additional_head_node: Optional[Node | list[Node]] = None,
    contain_in: str | None = "container mt-2",
    page_footer: bool = True,
) -> Node:
    """Base template for Pyplet web pages."""
    if not isinstance(content, list):
        content = [content]

    if contain_in is not None:
        content = [div(f".{contain_in.replace(' ', '.')}")[*content]]

    # Normalize additional_head_node to support unpacking if it's a list
    if additional_head_node is None:
        additional_head_node = []
    elif not isinstance(additional_head_node, list):
        additional_head_node = [additional_head_node]

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
            *additional_head_node,
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


# ---------------------------------------------------------------------------
# Navbar variants
# ---------------------------------------------------------------------------


def default_navbar(
    handler: RequestHandler, user: Optional[dict] = None
) -> Node:
    """Build the top navigation bar."""
    right_items_content = []

    if user and oauth.auth_enabled():
        # Authenticated: show name + logout
        display = user.get("name") or user.get("email") or "User"
        right_items_content = [
            li(".nav-item.dropdown")[
                a(
                    ".nav-link.dropdown-toggle",
                    href="#",
                    role="button",
                    data_bs_toggle="dropdown",
                    aria_expanded="false",
                )[display],
                ul(".dropdown-menu.dropdown-menu-end")[
                    li[
                        span(".dropdown-item-text.text-muted.small")[
                            user.get("email", "")
                        ]
                    ],
                    li[hr(".dropdown-divider")],
                    li[a(".dropdown-item", href="/logout")["Sign out"]],
                ],
            ]
        ]
    else:
        # Not authenticated or auth disabled: show "About" link
        right_items_content = [
            li(".nav-item")[a(".nav-link", href="/about")["About Pyplet"]]
        ]

    return nav(".navbar.navbar-expand-sm.bg-body-tertiary")[
        div(".container")[
            a(".navbar-brand", href="/")["Pyplet"],
            ul(".navbar-nav.ms-auto")[*right_items_content],
        ]
    ]


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------

_PROVIDER_ICONS = {
    "google": svg(
        xmlns="http://www.w3.org/2000/svg",
        viewBox="0 0 48 48",
        width="20",
        height="20",
        style="margin-right:8px",
    )[
        svg_path(
            fill="#EA4335",
            d="M24 9.5c3.1 0 5.8 1.1 8 2.9l6-6C34.5 3.1 29.6 1 24 1 14.9 1 "
            "7.1 6.5 3.5 14.3l7 5.4C12.3 13.6 17.7 9.5 24 9.5z",
        ),
        svg_path(
            fill="#4285F4",
            d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 "
            "7.2l7.4 5.7c4.3-4 6.8-9.9 6.8-16.9z",
        ),
        svg_path(
            fill="#FBBC05",
            d="M10.5 28.3A14.5 14.5 0 0 1 9.5 24c0-1.5.2-2.9.6-4.3L3.1 "
            "14.3A23.5 23.5 0 0 0 .5 24c0 3.8.9 7.4 2.6 10.6l7.4-6.3z",
        ),
        svg_path(
            fill="#34A853",
            d="M24 47c5.7 0 10.5-1.9 14-5.1l-7.4-5.7c-1.9 1.3-4.4 2-6.6 2-5.3 "
            "0-9.7-3.6-11.3-8.4l-7.4 5.7C7.1 41.5 14.9 47 24 47z",
        ),
    ],
    "microsoft": svg(
        xmlns="http://www.w3.org/2000/svg",
        viewBox="0 0 23 23",
        width="20",
        height="20",
        style="margin-right:8px",
    )[
        svg_path(fill="#f35325", d="M0 0h11v11H0z"),
        svg_path(fill="#81bc06", d="M12 0h11v11H12z"),
        svg_path(fill="#05a6f0", d="M0 12h11v11H0z"),
        svg_path(fill="#ffba08", d="M12 12h11v11H12z"),
    ],
}

_PROVIDER_LABEL = {"google": "Google", "microsoft": "Microsoft"}


def login_template(handler: RequestHandler) -> Node:
    """Login page shown to unauthenticated users."""
    next_url = handler.get_argument("next", "/")
    providers = oauth.enabled_providers()
    show_magiclink = magiclink.enabled()

    card_children = [h4(".mb-4.text-center")["Sign in to Pyplet"]]

    # ── OAuth provider buttons ──────────────────────────────────────────
    for provider in providers:
        icon_node = _PROVIDER_ICONS.get(provider, "")
        label_text = _PROVIDER_LABEL.get(provider, provider.title())
        card_children.append(
            a(
                ".btn.btn-outline-secondary.btn-lg.w-100"
                ".mb-3.text-start.d-flex.align-items-center",
                href=f"/oauth/login?provider={provider}&next={next_url}",
            )[icon_node, f"Continue with {label_text}"]
        )

    # ── Divider between OAuth and magic-link ────────────────────────────
    if providers and show_magiclink:
        card_children.append(
            div(".d-flex.align-items-center.my-3")[
                hr(".flex-grow-1"),
                span(".mx-2.text-muted.small")["or"],
                hr(".flex-grow-1"),
            ]
        )

    # ── Magic-link e-mail form ──────────────────────────────────────────
    if show_magiclink:
        card_children.append(
            form(method="POST", action="/auth/email")[
                input(type="hidden", name="_xsrf", value=""),
                input(type="hidden", name="next", value=next_url),
                div(".mb-2")[
                    label(".form-label.small.text-muted", for_="ml_email")[
                        "Sign in with e-mail"
                    ],
                    input(
                        ".form-control",
                        type="email",
                        name="email",
                        id="ml_email",
                        placeholder="you@example.com",
                        required=True,
                        autofocus=True if not providers else False,
                    ),
                ],
                button(".btn.btn-primary.w-100", type="submit")[
                    "Send sign-in link"
                ],
            ]
        )

    card = div(".card.shadow-sm.p-4")[*card_children]

    return base_template(
        page_title="Sign in",
        navbar=default_navbar(handler, user=None),
        content=div(".row.justify-content-center.mt-5")[
            div(".col-sm-5")[card]
        ],
    )


def magiclink_sent_template(handler: RequestHandler, email_addr: str) -> Node:
    """Confirmation page shown after a magic link has been sent."""
    ttl_min = config.magiclink_token_ttl // 60
    card = div(".card.shadow-sm.p-4.text-center")[
        div(style="font-size:3rem")["✉"],
        h4(".mt-3.mb-2")["Check your inbox"],
        p[
            "We sent a sign-in link to ",
            strong[email_addr],
            ".",
        ],
        p[
            span(".text-muted.small")[
                f"The link expires in {ttl_min} minute(s). "
            ]
        ],
        a(".btn.btn-outline-secondary.mt-2", href="/login")[
            "← Back to sign-in"
        ],
    ]
    return base_template(
        page_title="Check your inbox",
        navbar=default_navbar(handler, user=None),
        content=div(".row.justify-content-center.mt-5")[
            div(".col-sm-5")[card]
        ],
    )


# ---------------------------------------------------------------------------
# Index / home page
# ---------------------------------------------------------------------------


def index_template(
    handler: RequestHandler, user: Optional[dict] = None
) -> Node:
    """Home page listing applications."""
    email = user["email"] if user else ""
    projects = collections.defaultdict(list)

    if oauth.auth_enabled() and user:
        app_pairs = oauth.permitted_apps(email)
        for project, app_name in app_pairs:
            projects[project].append(
                li[a(href=f"apps/{project}/{app_name}")[app_name]]
            )
    else:
        # Auth disabled — show everything
        raw = [
            "/" + p[:-10]
            for p in sorted(glob.glob("*/*_client.py", root_dir=config.apps))
        ]
        for application in raw:
            project, app_name = application.split("/")[-2:]
            projects[project].append(
                li[a(href=f"apps/{project}/{app_name}")[app_name]]
            )

    if projects:
        application_list = ul[
            *[li[project, ul[*apps]] for project, apps in projects.items()]
        ]
        body_content = [
            p["Welcome to Pyplet!"],
            p["The following applications are available:"],
            application_list,
        ]
    else:
        body_content = [
            p["Welcome to Pyplet!"],
            p[
                (
                    em["No applications are available for your account."]
                    if oauth.auth_enabled()
                    else em["No applications have been installed yet."]
                )
            ],
        ]

    return base_template(
        page_title="Index",
        navbar=default_navbar(handler, user=user),
        content=body_content,
    )


# ---------------------------------------------------------------------------
# About page
# ---------------------------------------------------------------------------


def about_template(
    handler: RequestHandler, user: Optional[dict] = None
) -> Node:
    """About template for Pyplet web pages."""
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
                    "Its applications can be written entirely in Python while "
                    "leveraging two of the most vibrant programming "
                    "communities in the world: the JavaScript and Python "
                    "ecosystems."
                ],
            ]
        ],
    )


# ---------------------------------------------------------------------------
# App page template
# ---------------------------------------------------------------------------


def application_template(
    title: str, handler: RequestHandler, content: dict | Node | list
) -> Node:
    """Returns the application template for the given title and content."""
    additional_head = []
    body_content = []
    kwargs = {}

    if isinstance(content, dict):
        additional_head = content.get("head", [])
        body_content = content.get("body", [])
        if body_content:
            kwargs["contain_in"] = None
    else:
        if isinstance(content, list):
            body_content = content
        else:
            body_content = [content]

    user = oauth.get_session(handler) if oauth.auth_enabled() else None

    return base_template(
        page_title=title,
        navbar=default_navbar(handler, user=user),
        content=body_content,
        additional_head_node=additional_head,
        page_footer=False,
        **kwargs,
    )
