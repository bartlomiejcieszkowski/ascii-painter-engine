import ascii_painter_engine as ape
from ascii_painter_engine.widget import Pane


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = ape.App(log=ape.log.log)
    app.title = title
    app.color_mode()

    # TODO: Percent of window, relative
    pane = Pane(
        app=app,
        x=0,
        y=1,
        height=80,
        width=80,
        alignment=ape.Alignment.LeftTop,
        dimensions=ape.DimensionsFlag.Relative,
    )

    # TODO: alignment, only LeftTop does something
    pane.title = "Test"

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
