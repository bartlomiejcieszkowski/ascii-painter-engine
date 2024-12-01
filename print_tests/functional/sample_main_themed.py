#!/usr/bin/env python3
from pathlib import Path

import retui
from retui.theme import CssParser
from retui.widgets import Pane, TextBox
from src.retui import DefaultThemes
from src.retui.default_themes import DefaultThemesType


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App()
    app.title = title
    app.color_mode()

    # TODO: from script path and relpath
    working_directory = Path(__file__).parent
    files = [
        "css_parser/main.css",
    ]

    for file in files:
        selectors = CssParser.parse(working_directory / file, None)
        print(selectors)

    if demo_time_s is None:
        input("Press any key")

    widget = TextBox(app=app, x=0, y=0, height=4, width=20)
    widget.text = "This app should be themed"
    app.add_widget(widget)

    widget = Pane(app=app, x=2, y=8, height=4, width=8)
    widget.title = "Little Pane"
    app.add_widget(widget)

    pane = Pane(app=app, x=11, y=8, height=5, width=40)
    pane.title = "Bigger Pane"
    app.add_widget(pane)

    test_color = retui.ConsoleColor(retui.Color(13, retui.ColorBits.Bit8), retui.Color(7, retui.ColorBits.Bit8))

    widget = TextBox(app=app, x=0, y=0, height=3, width=10)
    widget.text = "Sample text in pane"
    widget.border_from_str(DefaultThemes.get_theme_border_str(DefaultThemesType.DOUBLE_LINE))
    widget.set_color(test_color)
    pane.add_widget(widget)

    widget = TextBox(app=app, x=10, y=0, height=3, width=25)
    widget.text = "TextBox without borders"
    widget.borderless = True
    pane.add_widget(widget)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
