#!/usr/bin/env python3
import retui
from retui.logger import log
from retui.widgets import Pane, TextBox


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App(log=log)
    app.title = title
    app.color_mode()

    widget = TextBox(app=app, x=0, y=0, height=4, width=20, alignment=retui.Alignment.TopLeft)
    widget.text = "Test"
    app.add_widget(widget)

    widget = Pane(app=app, x=2, y=8, height=4, width=8, alignment=retui.Alignment.TopLeft)
    widget.title = "Little Pane"
    app.add_widget(widget)

    pane = Pane(app=app, x=11, y=8, height=5, width=40, alignment=retui.Alignment.TopLeft)
    pane.title = "Bigger Pane"
    app.add_widget(pane)

    test_color = retui.ConsoleColor(retui.Color(13, retui.ColorBits.Bit8), retui.Color(7, retui.ColorBits.Bit8))

    widget = TextBox(
        app=app, x=0, y=0, height=3, width=10, alignment=retui.Alignment.TopLeft, text_align=retui.TextAlign.BottomRight
    )
    widget.text = "Sample text in pane"
    widget.border_from_str(" /\\\\/-||-")
    widget.border_set_color(test_color)
    pane.add_widget(widget)

    widget = TextBox(
        app=app,
        x=10,
        y=0,
        height=3,
        width=25,
        alignment=retui.Alignment.TopLeft,
        text_align=retui.TextAlign.BottomRight,
    )
    widget.text = "TextBox without borders"
    widget.borderless = True
    pane.add_widget(widget)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
