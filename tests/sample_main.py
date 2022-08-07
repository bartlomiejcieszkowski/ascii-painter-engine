#!/usr/bin/env python3


import ascii_painter_engine as ape


def test(handle_sigint=True):
    console_view = ape.App(log=ape.log.log)
    console_view.color_mode()

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=0, y=0, height=4, width=20,
                                        alignment=ape.Alignment.LeftTop)
    widget.text = 'Test'
    console_view.add_widget(widget)

    widget = ape.ConsoleWidgets.Pane(console_view=console_view, x=2, y=8, height=4, width=8,
                                     alignment=ape.Alignment.LeftTop)
    widget.title = 'Little Pane'
    console_view.add_widget(widget)

    pane = ape.ConsoleWidgets.Pane(console_view=console_view, x=11, y=8, height=5, width=40,
                                   alignment=ape.Alignment.LeftTop)
    pane.title = 'Bigger Pane'
    console_view.add_widget(pane)

    test_color = ape.ConsoleColor(ape.Color(14, ape.ColorBits.Bit8), ape.Color(4, ape.ColorBits.Bit8))

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=0, y=0, height=3, width=10,
                                        alignment=ape.Alignment.LeftTop)
    widget.text = 'Sample text in pane'
    widget.border_from_str(' /\\\\/-||-')
    widget.border_set_color(test_color)
    pane.add_widget(widget)

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=10, y=0, height=3, width=25,
                                        alignment=ape.Alignment.LeftTop)
    widget.text = 'TextBox without borders'
    widget.borderless = True
    pane.add_widget(widget)

    console_view.loop(handle_sigint)
