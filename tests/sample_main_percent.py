import ascii_painter_engine as ape
from ascii_painter_engine.widget import Pane


def test(handle_sigint=True, demo_time_s=None):
    app = ape.App(log=ape.log.log)
    app.color_mode()

    # TODO: Percent of window, fill
    pane = Pane(app=app, x=0, y=1, height=80, width=100, alignment=ape.Alignment.LeftTop, percent=True)
    pane.title = 'Test'

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
