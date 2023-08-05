import retui
from retui.logger import log
from retui.widget import Pane


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App(log=log)
    app.title = title
    app.color_mode()

    # TODO: Percent of window, relative
    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=80,
        width=80,
        alignment=retui.Alignment.TopLeft,
        dimensions=retui.DimensionsFlag.Relative,
    )

    # TODO: alignment, only TopLeft does something
    pane.title = "Test"

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
