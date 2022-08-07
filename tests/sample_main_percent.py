import ascii_painter_engine as ape


def test():
    app = ape.App(log=ape.log.log)
    app.color_mode()

    # TODO: Percent of window, fill
    pane = ape.ConsoleWidgets.Pane(app=app, x=0, y=1, height=80, width=100,
                                   alignment=ape.Alignment.LeftTop, percent=True)
    pane.title = 'Test'

    app.add_widget(pane)

    app.run()
