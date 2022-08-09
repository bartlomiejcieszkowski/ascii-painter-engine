import ascii_painter_engine as ape
from ascii_painter_engine.widget import Pane


def test(handle_sigint=True, demo_time_s=None):
    app = ape.App(log=ape.log.log)
    app.color_mode()

    pane = Pane(app=app, x=0, y=0, height=80, width=100, alignment=ape.Alignment.Center, dimensions=ape.DimensionsFlag.Fill)
    # dimensions should be ignored for Fill
    pane.title = 'Test'

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
