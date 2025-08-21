import pyplet.common.dom as d
from js import document, console, jQuery as jQ
from pyodide.ffi import create_proxy

container = document.getElementById("container")


@create_proxy
def new_window(e):
    tree = d.div(title="text").append(
        d.iframe(
            src="/",
            frameborder="0",
            style="overflow:hidden;height:100%;width:100%",
            width="100%",
            height="100%",
        )
    )

    @create_proxy
    def close(event, _):
        iframe.src = "/"

    div = tree._render_dom(document)
    container.appendChild(div)
    iframe = div.firstChild
    iframe.addEventListener("load", hide_bar)

    jQ(container.lastChild).dialog().on("dialogclose", close)


tree = d.div(
    d.button("New window", id="new_window_button").on("click", new_window),
)
container.appendChild(tree._render_dom(document))


@create_proxy
def hide_bar(event):
    jQ(".navbar", event.target.contentDocument).remove()
    jQ(".footer", event.target.contentDocument).remove()
    console.log(jQ(".ui-dialog-title", event.target.parentNode))
    jQ(".ui-dialog-title", jQ(event.target.parentNode).closest(".ui-dialog")).text(
        event.target.contentDocument.title
    )
