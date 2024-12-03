import importlib

_APP_DICT = {}
_OFFICIAL_WIDGET_DICT = {}
_APP_WIDGET_DICT = {}
_MODULES_DICT = {}


def register_mapping_dict(name, app_dict):
    global _APP_DICT
    _APP_DICT[name] = app_dict


def official_widget(cls):
    global _OFFICIAL_WIDGET_DICT
    _OFFICIAL_WIDGET_DICT[cls.__name__] = cls
    return cls


def app_widget(cls):
    global _APP_WIDGET_DICT
    _APP_WIDGET_DICT[cls.__name__] = cls
    return cls


def log_widgets(log_fn=print):
    log_fn("OFFICIAL WIDGETS:")
    for name, cls in _OFFICIAL_WIDGET_DICT.items():
        log_fn(f'"{name}": {cls}')
    log_fn("APP WIDGETS:")
    for name, cls in _APP_WIDGET_DICT.items():
        log_fn(f'"{name}": {cls}')


def get_widget_class(name: str):
    widget_class = _APP_WIDGET_DICT.get(name, None)
    if widget_class is None:
        widget_class = _OFFICIAL_WIDGET_DICT.get(name, None)
    return widget_class


def import_widget_class(name: str, ctx_globals: dict):
    """
    New widgets are registered in _APP_WIDGET_DICT using full name.
    Imported modules are also cached as they might provide more widgets.

    :param name: widget class name e.g. sample_app.widgets.CustomWidget
    :param ctx_globals: application globals, usually globals()
    :return widget class
    """

    global _MODULES_DICT
    last_dot = name.rfind(".")
    if last_dot >= 0 and last_dot + 1 < len(name):
        module_name, class_name = name.rsplit(".", 1)

        m = _MODULES_DICT.get(module_name, None)
        if m is None:
            m = importlib.import_module(module_name)
            if m is None:
                return None
            _MODULES_DICT[module_name] = m

        # now try to get class
        cls = getattr(m, class_name)
    else:
        # this should be class name without dots, so it should be in theory available in globals
        cls = ctx_globals.get(name)

    if cls is None:
        return None

    global _APP_WIDGET_DICT
    _APP_WIDGET_DICT[name] = cls
    return cls


def is_mapping(value):
    return type(value) is str and value.startswith("__")


def get_mapping(value):
    path = value[2:]
    steps = path.split("#")
    curr_dict = _APP_DICT
    for step in steps[:-1]:
        curr_dict = curr_dict.get(step, None)
        if curr_dict is None:
            raise Exception(f"No mapping for '{value}', recheck register_app_dict calls")
    mapping_value = curr_dict.get(steps[-1], None)
    if mapping_value is None:
        raise Exception(f"No mapping for '{value}', recheck register_app_dict calls")

    return mapping_value
