def get_import(module_name):
    mod = __import__(module_name)
    for k in module_name.split(".")[1:]:
        mod = getattr(mod, k)
    return mod
