#!/usr/bin/env python3
import retui
from retui.default_themes import DefaultThemes, DefaultThemesType
from retui.widgets import Pane, TextBox


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App()
    app.title = title
    app.color_mode()

    widget = TextBox(app=app, x=0, y=0, height=4, width=20, dock=retui.Dock.NONE)
    widget.text = "Test"
    app.add_widget(widget)

    widget = Pane(app=app, x=2, y=8, height=4, width=8, dock=retui.Dock.NONE)
    widget.title = "Little Pane"
    app.add_widget(widget)

    pane = Pane(app=app, x=11, y=8, height=5, width=40, dock=retui.Dock.NONE)
    pane.title = "Bigger Pane"
    app.add_widget(pane)

    test_color = retui.TerminalColor(retui.Color(13, retui.ColorBits.Bit8), retui.Color(7, retui.ColorBits.Bit8))

    widget = TextBox(
        app=app, x=0, y=0, height=3, width=10, dock=retui.Dock.NONE, text_align=retui.TextAlign.BottomRight
    )
    widget.text = "Sample text in pane"
    widget.border_from_str(DefaultThemes.get_theme_border_str(DefaultThemesType.DOUBLE_TOP))
    widget.set_color(test_color)
    pane.add_widget(widget)

    widget = TextBox(
        app=app,
        x=10,
        y=0,
        height=3,
        width=25,
        dock=retui.Dock.NONE,
        text_align=retui.TextAlign.BottomRight,
    )
    widget.text = "TextBox without borders"
    widget.borderless = True
    pane.add_widget(widget)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
