"""Client-side convenience utilities.

Small helpers that simplify bridging between Python and JS in Pyodide, plus a
helper to render Matplotlib figures into a specific container.

Docstring style: Google.
"""

import warnings

from js import console, document, window, Object
from pyodide.ffi import create_proxy, to_js


def create_proxy_with_this(callable):
    """Create a proxy and capture JS ``this`` context when invoked."""
    return create_proxy(callable).captureThis()


def to_js_obj(kwargs):
    """Convert a Python mapping to a JS ``Object`` preserving keys and values."""
    return Object.fromEntries(to_js(kwargs))


try:
    import matplotlib.pyplot as plt

    with warnings.catch_warnings(action="ignore"):
        plt.rcParams["toolbar"] = "toolmanager"
except ImportError:
    pass


def show_plot(target):
    """Show the current Matplotlib figure inside ``target`` element.

    Also strips Matplotlib's toolbars for a cleaner embedded look and returns
    the plot node that was mounted.
    """
    import matplotlib.pyplot as plt

    fig = plt.gcf()
    document.pyodideMplTarget = target
    plt.show()

    # Remove tools
    # visually
    plot = target.lastChild
    plot.removeChild(plot.lastChild)
    plot.removeChild(plot.firstChild)
    # logically
    for t in fig.canvas.manager.toolmanager.tools:
        fig.canvas.manager.toolmanager.remove_tool(t)
    return plot
