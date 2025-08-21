import matplotlib.pyplot as plt
import json
import numpy as np
import pyplet

from js import document

fig = plt.figure()
lines = None


async def websocket_client_loop(ws: pyplet.WebSocket):
    history = None
    lines = {}
    while True:
        if history is None:
            history = json.loads(await ws.receive())
            for l in history:
                (lines[l],) = plt.plot(history[l])
            plt.legend(list(history))
            plt.show()
            document.getElementById("container").appendChild(document.body.lastChild)
        else:
            msg = await ws.receive()
            if msg is ws.closing_message:
                break
            live = json.loads(msg)
            for l in live:
                history[l].append(live[l])
                lines[l].set_ydata(history[l])
                lines[l].set_xdata(np.arange(len(history[l])))
            plt.gca().relim()
            plt.gca().autoscale_view()
            plt.draw()
