#!/usr/bin/env python3


import ascii_painter_engine as ape
from ascii_painter_engine.widget import TextBox, Pane


def test(handle_sigint=True, demo_time_s=None):
    app = ape.App(log=ape.log.log)
    app.color_mode()

    widget = TextBox(app=app, x=0, y=0, height=4, width=20, alignment=ape.Alignment.LeftTop)
    widget.text = 'Test'
    app.add_widget(widget)

    widget = Pane(app=app, x=2, y=8, height=4, width=8, alignment=ape.Alignment.LeftTop)
    widget.title = 'Little Pane'
    app.add_widget(widget)

    pane = Pane(app=app, x=11, y=8, height=5, width=40, alignment=ape.Alignment.LeftTop)
    pane.title = 'Bigger Pane'
    app.add_widget(pane)

    test_color = ape.ConsoleColor(ape.Color(14, ape.ColorBits.Bit8), ape.Color(4, ape.ColorBits.Bit8))

    widget = TextBox(app=app, x=0, y=0, height=3, width=10, alignment=ape.Alignment.LeftTop)
    widget.text = 'Sample text in pane'
    widget.border_from_str(' /\\\\/-||-')
    widget.border_set_color(test_color)
    pane.add_widget(widget)

    widget = TextBox(app=app, x=10, y=0, height=3, width=25, alignment=ape.Alignment.LeftTop)
    widget.text = 'TextBox without borders'
    widget.borderless = True
    pane.add_widget(widget)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
