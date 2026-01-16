from js import document, console
from pyodide.ffi import create_proxy
import pyplet
import json
from pyplet.client import ClientApplication

container = document.getElementById("container")
input = document.createElement("input")
input.setAttribute("type", "text")
container.appendChild(input)


def decode(msg):
    msg = json.loads(msg)
    if msg["type"] == "error":
        render(f"<b>ERROR</b>: {msg['message']}")
        raise msg["message"]
    return msg


def render(html):
    p = document.createElement("p")
    p.innerHTML = html
    container.appendChild(p)


class _(ClientApplication):
    async def websocket_client_loop(self, ws: pyplet.WebSocket):
        init = decode(await ws.receive())
        assert init["type"] == "init"
        render(f"<b>Logged in as {init['name']}</b>")

        @create_proxy
        async def submit(_):
            message = input.value
            input.value = ""
            await ws.send(message)

        input.addEventListener("change", submit)

        while True:
            msg = await ws.receive()
            if msg is ws.closing_message:
                break
            msg = decode(msg)
            render(f"<b>{msg['name']}</b>: {msg['message']}")
        render(f"<b>Server disconnected</b>")
