from .dom import script, link


pyscript_2024_11_1 = [
    link(rel="stylesheet", href="https://pyscript.net/releases/2024.11.1/core.css"),
    script(type="module", src="https://pyscript.net/releases/2024.11.1/core.js"),
]

jquery_3_7_1 = [
    script(
        src="https://code.jquery.com/jquery-3.7.1.min.js",
        integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo=",
        crossorigin="anonymous",
    ),
]

jquery_ui_1_14_1 = [
    link(
        rel="stylesheet",
        href="https://code.jquery.com/ui/1.14.1/themes/base/jquery-ui.css",
    ),
    script(
        src="https://code.jquery.com/ui/1.14.1/jquery-ui.min.js",
        integrity="sha256-AlTido85uXPlSyyaZNsjJXeCs07eSv3r43kyCVc8ChI=",
        crossorigin="anonymous",
    ),
]

d3_7_9_0 = [
    script(
        src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js",
        integrity="sha512-vc58qvvBdrDR4etbxMdlTt4GBQk1qjvyORR2nrsPsFPyrs+/u5c3+1Ct6upOgdZoIl7eq6k3a1UPDSNAQi/32A==",
        crossorigin="anonymous",
    )
]
