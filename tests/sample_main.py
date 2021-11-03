#!/usr/bin/env python3


import ascii_painter_engine as ape


def test(handle_sigint=True):
    console_view = ape.ConsoleView(debug=True)
    console_view.color_mode()

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=2, y=2, height=4, width=20,
                                        alignment=ape.ConsoleWidgetAlignment.LeftTop)
    widget.text = 'Test'
    console_view.add_widget(widget)

    widget = ape.ConsoleWidgets.Pane(console_view=console_view, x=2, y=8, height=4, width=8,
                                     alignment=ape.ConsoleWidgetAlignment.LeftTop)
    widget.title = 'Little Pane'
    console_view.add_widget(widget)

    pane = ape.ConsoleWidgets.Pane(console_view=console_view, x=11, y=8, height=5, width=40,
                                   alignment=ape.ConsoleWidgetAlignment.LeftTop)
    pane.title = 'Bigger Pane'
    console_view.add_widget(pane)

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=0, y=0, height=3, width=10,
                                        alignment=ape.ConsoleWidgetAlignment.LeftTop)
    widget.text = 'Sample text in pane'
    widget.border_from_str(' /\\\\/-||-')
    widget.border_set_color((14, 4))
    pane.add_widget(widget)

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=10, y=0, height=3, width=25,
                                        alignment=ape.ConsoleWidgetAlignment.LeftTop)
    widget.text = 'TextBox without borders'
    widget.borderless = True
    pane.add_widget(widget)

    console_view.loop(handle_sigint)
