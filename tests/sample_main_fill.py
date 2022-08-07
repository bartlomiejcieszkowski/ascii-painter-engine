import ascii_painter_engine as ape


def test():
    app = ape.App(log=ape.log.log)
    app.color_mode()

    pane = ape.ConsoleWidgets.Pane(app=app, x=0, y=0, height=80, width=100,
                                   alignment=ape.Alignment.Center, dimensions=ape.DimensionsFlag.Fill)
    # dimensions should be ignored for Fill
    pane.title = 'Test'

    app.add_widget(pane)

    app.run()
