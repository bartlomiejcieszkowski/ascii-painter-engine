import ascii_painter_engine as ape


def test():
    console_view = ape.App(log=ape.log.log)
    console_view.color_mode()

    pane = ape.ConsoleWidgets.Pane(console_view=console_view, x=0, y=1, height=80, width=100,
                                   alignment=ape.Alignment.LeftTop)
    pane.title = 'Test'

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=0, y=0, height=20, width=40, alignment=ape.Alignment.FloatLeftTop)
    widget.text = '1st float'
    pane.add_widget(widget)

    # pane inside:
    # 1111
    # 1111
    #
    #


    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=0, y=0, height=30, width=60,
                                        alignment=ape.Alignment.FloatLeftTop)
    widget.text = '2nd float'
    pane.add_widget(widget)

    # pane inside:
    # 1111222222
    # 1111222222
    #     222222
    #

    widget = ape.ConsoleWidgets.TextBox(console_view=console_view, x=0, y=0, height=20, width=30,
                                        alignment=ape.Alignment.FloatLeftTop)
    widget.text = '3rd float'
    pane.add_widget(widget)

    # pane inside:
    # 1111222222
    # 1111222222
    # 333 222222
    # 333


    console_view.add_widget(pane)

    console_view.loop(True)
