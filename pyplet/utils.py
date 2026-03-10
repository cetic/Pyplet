"""Utility helpers.

This module currently exposes a small dynamic import helper used by the
server-side packaging/dispatch and the client bootstrap.

Docstring style: Google.
"""


def get_import(module_name: str):
    """Dynamically import and return a nested module.

    Args:
        module_name: Dotted module path (e.g. ``"apps.examples.chat_client"``).

    Returns:
        The imported module object referenced by ``module_name``.
    """
    mod = __import__(module_name)
    for k in module_name.split(".")[1:]:
        mod = getattr(mod, k)

    return mod
