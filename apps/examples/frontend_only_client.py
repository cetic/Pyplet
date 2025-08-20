from js import document
from pyplet.common import dom as d
import matplotlib.pyplot as plt
import numpy as np

tree = d.div(
    d.p("This is a frontend-only app."),
    d.p("Yet, it can leverage matplotlib, numpy, ... ", "How cool is that?"),
)
document.getElementById("container").appendChild(tree._render_dom(document))

x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.plot(x, y)
plt.show()
document.getElementById("container").appendChild(document.body.lastChild)
