from js import console, document

import numpy as np

document.pyodideMplTarget = document.getElementById("container")

import matplotlib.pyplot as plt
import io


async def websocket_client_loop(ws):
    im = None
    fig = plt.figure()
    while True:
        array = np.load(io.BytesIO(await ws.receive()))
        if im is None:
            im = fig.gca().imshow(array, vmin=-4, vmax=4)
            plt.show()
        else:
            im.set_data(array)
            plt.draw()
