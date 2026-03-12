import warnings

from js import Object, document
from pyodide.ffi import create_proxy, to_js


def create_proxy_with_this(callable):
    return create_proxy(callable).captureThis()


def to_js_obj(kwargs):
    return Object.fromEntries(to_js(kwargs))


try:
    import matplotlib.pyplot as plt

    with warnings.catch_warnings(action="ignore"):
        plt.rcParams["toolbar"] = "toolmanager"
except ImportError:
    pass


def show_plot(target):
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
