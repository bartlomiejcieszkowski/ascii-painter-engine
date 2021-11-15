import ascii_painter_engine as ape


def test():
    console_view = ape.ConsoleView(log=ape.log.log)
    console_view.color_mode()

    pane = ape.ConsoleWidgets.Pane(console_view=console_view, x=0, y=0, height=80, width=100,
                                   alignment=ape.Alignment.Center, dimensions=ape.DimensionsFlag.Fill)
    # dimensions should be ignored for Fill
    pane.title = 'Test'

    console_view.add_widget(pane)

    console_view.loop(True)
