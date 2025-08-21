from .. import dom as d
from ..dom import bootstrap as b
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


def default_navbar(handler):
    return b.nav(_class="navbar navbar-expand-sm bg-body-tertiary").append(
        d.div(_class="container").append(
            # Brand
            d.a("Pyplet", _class="navbar-brand", href="/"),
            # Right menu
            d.ul(_class="navbar-nav ms-auto").append(
                # About
                d.li(_class="nav-item").append(
                    d.a("About Pyplet", href="/about", _class="nav-link"),
                ),
            ),
        )
    )


def new_password_confirmation(handler, email):
    return base_template(
        title="New password confirmation",
        navbar=default_navbar(handler),
        content=[
            d.p(f"A new password has been sent to your e-mail: {email}."),
            d.p(f"Please check your spams!"),
            d.form(action="/", method="post").append(
                d.input(
                    type="hidden",
                    name="email",
                    label="Your email address",
                    _class="form-control",
                    value="email",
                ),
                d.input(
                    type="password",
                    name="password",
                    label="You password",
                    _class="form-control",
                )
                | d.label("Password", "row mb-2", "col-sm-2, col-sm-5"),
                d.input(
                    type="submit",
                    value="Login",
                    _class="btn btn-primary col-sm-5 offset-sm-1",
                ),
            ),
            d.p(d.a("Back to the login page", href="/")),
        ],
    )


def index_template(handler):
    applications = ["/" + p[:-10] for p in sorted(glob.glob("apps/*/*_client.py"))]
    projects = collections.defaultdict(d.ul)
    for application in applications:
        project, app_name = application.split("/")[-2:]
        projects[project].append(d.li(d.a(app_name, href=application)))
    application_list = d.ul(
        *[d.li(project, apps) for project, apps in projects.items()]
    )
    return base_template(
        title="Index",
        navbar=default_navbar(handler),
        content=[
            d.p(f"Welcome to Pyplet!"),
            d.p(f"The following applications are available:"),
            application_list,
        ],
    )


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
                    " to provide its partners with tailor-made and easily accessible annotation applications.",
                ),
                d.p(
                    "Its applications can be written entirely in Python while leveraging two of the most vibrant programming "
                    "communities in the world: the JavaScript and Python ecosystems."
                ),
            ),
        ],
    )


def application_template(title, handler, content: d.Node):
    additional_head = ()
    kwargs = {}
    if content and getattr(content[0], "tag", None) == "head":
        additional_head = content[0].children
        content = content[1:]
    if content and getattr(content[0], "tag", None) == "body":
        kwargs["contain_in"] = None
        content = content[0].children

    return base_template(
        title=title,
        navbar=default_navbar(handler),
        content=content,
        additional_head=additional_head,
        footer=False,
        **kwargs,
    )
