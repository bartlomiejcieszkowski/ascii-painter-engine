from ascii_painter_engine import widget

WIDGET_DICT = {
    "TextBox": widget.TextBox,
    "Pane": widget.Pane,
    "BorderWidget": widget.BorderWidget,
    "Button": widget.Button,
}


def GetWidgetClass(name: str):
    return WIDGET_DICT.get(name, None)
