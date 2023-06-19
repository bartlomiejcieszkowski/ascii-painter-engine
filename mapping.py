import importlib

from ascii_painter_engine import widget

WIDGET_DICT = {
    "TextBox": widget.TextBox,
    "Pane": widget.Pane,
    "BorderWidget": widget.BorderWidget,
    "Button": widget.Button,
}

MODULES_DICT = {}


def get_widget_class(name: str):
    return WIDGET_DICT.get(name, None)


def import_widget_class(name: str):
    # New widgets are registered in WIDGET_DICT
    # using full name
    # Modules imported are also cached
    # As they might provide more widgets
    global MODULES_DICT
    last_dot = name.rfind(".")
    if last_dot >= 0 and last_dot + 1 < len(name):
        module_name, class_name = name.rsplit(".", 1)

        m = MODULES_DICT.get(module_name, None)
        if m is None:
            m = importlib.import_module(module_name)
            if m is None:
                return None
            MODULES_DICT[module_name] = m

        # now try to get class
        cls = getattr(m, class_name)
    else:
        # this should be class name without dots, so it should be in theory available in globals
        cls = globals().get(name)

    if cls is None:
        return None

    global WIDGET_DICT
    WIDGET_DICT[name] = cls
    return cls
