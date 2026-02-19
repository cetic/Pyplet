from ..shared import dom as d
from ..shared.dom import bootstrap as b
from . import config
from . import oauth
from . import magiclink
import typing as t
import collections
import glob
from dataclasses import dataclass


def base_template(
    *,
    title=None,
    navbar,
    content,
    additional_head=(),
    contain_in="container mt-2",
    footer=True,
):
    if contain_in is not None:
        content = (d.div(_class=contain_in).append(*content),)
    return d.html("<!doctype html>", lang="en", _class="h-100").append(
        d.head(
            d.meta(charset="utf-8"),
            d.meta(name="viewport", content="width=device-width, initial-scale=1"),
            d.title(f"{title} - Pyplet" if title else "Pyplet"),
            d.link(
                href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
                rel="stylesheet",
                integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH",
                crossorigin="anonymous",
            ),
            *additional_head,
        ),
        d.body(_class="d-flex flex-column h-100").append(
            d.main(_class="flex-fill").append(
                navbar,
                *content,
            ),
            (
                d.footer(_class="footer mt-auto py-3 bg-light").append(
                    d.div(_class="container").append(
                        d.span(_class="text-muted").append(
                            "&copy; Copyright CETIC 2024 - 2025. All rights reserved",
                        )
                    )
                )
                if footer
                else d.footer(_class="footer mt-auto")
            ),
            d.script(
                src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
                integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz",
                crossorigin="anonymous",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Navbar variants
# ---------------------------------------------------------------------------

def default_navbar(handler, user: dict | None = None):
    """
    Build the top navigation bar.

    When *user* is provided (authenticated request) a user menu with a
    logout link is shown on the right side.  When auth is disabled, the
    navbar looks exactly as before.
    """
    right_items = d.ul(_class="navbar-nav ms-auto")

    if user and oauth.auth_enabled():
        # Authenticated: show name + logout
        display = user.get("name") or user.get("email") or "User"
        right_items.append(
            d.li(_class="nav-item dropdown").append(
                d.a(
                    display,
                    _class="nav-link dropdown-toggle",
                    href="#",
                    role="button",
                    data_bs_toggle="dropdown",
                    aria_expanded="false",
                ),
                d.ul(_class="dropdown-menu dropdown-menu-end").append(
                    d.li(
                        d.span(
                            user.get("email", ""),
                            _class="dropdown-item-text text-muted small",
                        )
                    ),
                    d.li(d.hr(_class="dropdown-divider")),
                    d.li(d.a("Sign out", href="/logout", _class="dropdown-item")),
                ),
            )
        )
    else:
        # Not authenticated or auth disabled: show "About" link
        right_items.append(
            d.li(_class="nav-item").append(
                d.a("About Pyplet", href="/about", _class="nav-link"),
            )
        )

    return b.nav(_class="navbar navbar-expand-sm bg-body-tertiary").append(
        d.div(_class="container").append(
            d.a("Pyplet", _class="navbar-brand", href="/"),
            right_items,
        )
    )


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------

_PROVIDER_ICONS = {
    "google": (
        # Inline SVG Google "G" logo (official brand colours)
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="20" height="20" style="margin-right:8px">'
        '<path fill="#EA4335" d="M24 9.5c3.1 0 5.8 1.1 8 2.9l6-6C34.5 3.1 29.6 1 24 1 14.9 1 7.1 6.5 3.5 14.3l7 5.4C12.3 13.6 17.7 9.5 24 9.5z"/>'
        '<path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.4 5.7c4.3-4 6.8-9.9 6.8-16.9z"/>'
        '<path fill="#FBBC05" d="M10.5 28.3A14.5 14.5 0 0 1 9.5 24c0-1.5.2-2.9.6-4.3L3.1 14.3A23.5 23.5 0 0 0 .5 24c0 3.8.9 7.4 2.6 10.6l7.4-6.3z"/>'
        '<path fill="#34A853" d="M24 47c5.7 0 10.5-1.9 14-5.1l-7.4-5.7c-1.9 1.3-4.4 2-6.6 2-5.3 0-9.7-3.6-11.3-8.4l-7.4 5.7C7.1 41.5 14.9 47 24 47z"/>'
        "</svg>"
    ),
    "microsoft": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 23 23" width="20" height="20" style="margin-right:8px">'
        '<path fill="#f35325" d="M0 0h11v11H0z"/>'
        '<path fill="#81bc06" d="M12 0h11v11H12z"/>'
        '<path fill="#05a6f0" d="M0 12h11v11H0z"/>'
        '<path fill="#ffba08" d="M12 12h11v11H12z"/>'
        "</svg>"
    ),
}

_PROVIDER_LABEL = {"google": "Google", "microsoft": "Microsoft"}


def login_template(handler):
    """
    Login page shown to unauthenticated users.

    Shows one button per configured OAuth provider, and/or a magic-link
    e-mail form when magic-link auth is configured.  Sections are separated
    by a visible divider when both are present.
    """
    next_url = handler.get_argument("next", "/")
    providers = oauth.enabled_providers()
    show_magiclink = magiclink.enabled()

    card_children = [d.h4("Sign in to Pyplet", _class="mb-4 text-center")]

    # ── OAuth provider buttons ──────────────────────────────────────────
    for provider in providers:
        icon_html = _PROVIDER_ICONS.get(provider, "")
        label = _PROVIDER_LABEL.get(provider, provider.title())
        card_children.append(
            d.a(
                icon_html + f"Continue with {label}",
                href=f"/oauth/login?provider={provider}&next={next_url}",
                _class="btn btn-outline-secondary btn-lg w-100 mb-3 text-start d-flex align-items-center",
            )
        )

    # ── Divider between OAuth and magic-link ────────────────────────────
    if providers and show_magiclink:
        card_children.append(
            d.div(_class="d-flex align-items-center my-3").append(
                d.hr(_class="flex-grow-1"),
                d.span("or", _class="mx-2 text-muted small"),
                d.hr(_class="flex-grow-1"),
            )
        )

    # ── Magic-link e-mail form ──────────────────────────────────────────
    if show_magiclink:
        card_children.append(
            d.form(method="POST", action=f"/auth/email").append(
                d.input(
                    type="hidden",
                    name="_xsrf",
                    value="",   # Tornado XSRF is not used here; form is self-contained
                ),
                d.input(
                    type="hidden",
                    name="next",
                    value=next_url,
                ),
                d.div(_class="mb-2").append(
                    d.label("Sign in with e-mail", _for="ml_email",
                            _class="form-label small text-muted"),
                    d.input(
                        type="email",
                        name="email",
                        id="ml_email",
                        _class="form-control",
                        placeholder="you@example.com",
                        required="required",
                        autofocus="autofocus" if not providers else None,
                    ),
                ),
                d.button(
                    "Send sign-in link",
                    type="submit",
                    _class="btn btn-primary w-100",
                ),
            )
        )

    card = d.div(_class="card shadow-sm p-4").append(*card_children)

    return base_template(
        title="Sign in",
        navbar=default_navbar(handler, user=None),
        content=[
            d.div(_class="row justify-content-center mt-5").append(
                d.div(_class="col-sm-5").append(card)
            )
        ],
    )


def magiclink_sent_template(handler, email_addr: str):
    """
    Confirmation page shown after a magic link has been sent.
    """
    ttl_min = config.magiclink_token_ttl // 60
    card = d.div(_class="card shadow-sm p-4 text-center").append(
        d.div("✉", style="font-size:3rem"),
        d.h4("Check your inbox", _class="mt-3 mb-2"),
        d.p(
            "We sent a sign-in link to ",
            d.strong(email_addr),
            ".",
        ),
        d.p(
            d.span(f"The link expires in {ttl_min} minute(s). ", _class="text-muted small"),
        ),
        d.a("← Back to sign-in", href="/login", _class="btn btn-outline-secondary mt-2"),
    )
    return base_template(
        title="Check your inbox",
        navbar=default_navbar(handler, user=None),
        content=[
            d.div(_class="row justify-content-center mt-5").append(
                d.div(_class="col-sm-5").append(card)
            )
        ],
    )


# ---------------------------------------------------------------------------
# Index / home page
# ---------------------------------------------------------------------------

def index_template(handler, user: dict | None = None):
    """
    Home page listing applications.

    When auth is enabled, only apps the user is permitted to access are shown.
    When auth is disabled, all apps are shown (original behaviour).
    """
    email = user["email"] if user else ""

    if oauth.auth_enabled() and user:
        app_pairs = oauth.permitted_apps(email)
        projects = collections.defaultdict(d.ul)
        for project, app_name in app_pairs:
            projects[project].append(
                d.li(d.a(app_name, href=f"apps/{project}/{app_name}"))
            )
    else:
        # Auth disabled — show everything (original behaviour)
        raw = [
            "/" + p[:-10]
            for p in sorted(glob.glob("*/*_client.py", root_dir=config.apps))
        ]
        projects = collections.defaultdict(d.ul)
        for application in raw:
            project, app_name = application.split("/")[-2:]
            projects[project].append(
                d.li(d.a(app_name, href=f"apps/{project}/{app_name}"))
            )

    if projects:
        application_list = d.ul(
            *[d.li(project, apps) for project, apps in projects.items()]
        )
        body_content = [
            d.p("Welcome to Pyplet!"),
            d.p("The following applications are available:"),
            application_list,
        ]
    else:
        body_content = [
            d.p("Welcome to Pyplet!"),
            d.p(
                d.em("No applications are available for your account.")
                if oauth.auth_enabled()
                else d.em("No applications have been installed yet.")
            ),
        ]

    return base_template(
        title="Index",
        navbar=default_navbar(handler, user=user),
        content=body_content,
    )


# ---------------------------------------------------------------------------
# About page (unchanged)
# ---------------------------------------------------------------------------

def about_template(handler):
    return base_template(
        title="About",
        navbar=default_navbar(handler),
        content=[
            d.div(_class="col-sm-8 mx-auto").append(
                d.p("Pyplet is a full-Python application server."),
                d.p(
                    "It is developed at the ",
                    d.a("CETIC", href="https://www.cetic.be/", target="_blank"),
                    " to develop web applications.",
                ),
                d.p(
                    "Its applications can be written entirely in Python while leveraging two of the most vibrant programming "
                    "communities in the world: the JavaScript and Python ecosystems."
                ),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# App page template (unchanged)
# ---------------------------------------------------------------------------

def application_template(title, handler, content: d.Node):
    additional_head = ()
    kwargs = {}
    if content and getattr(content[0], "tag", None) == "head":
        additional_head = content[0].children
        content = content[1:]
    if content and getattr(content[0], "tag", None) == "body":
        kwargs["contain_in"] = None
        content = content[0].children

    user = oauth.get_session(handler) if oauth.auth_enabled() else None

    return base_template(
        title=title,
        navbar=default_navbar(handler, user=user),
        content=content,
        additional_head=additional_head,
        footer=False,
        **kwargs,
    )
