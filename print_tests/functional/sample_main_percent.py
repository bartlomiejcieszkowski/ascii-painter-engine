import retui
from retui.widgets import Pane


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App()
    app.title = title
    app.color_mode()

    # TODO: Percent of window, relative
    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=80,
        width=80,
        dock=retui.Dock.NONE,
        dimensions=retui.DimensionsFlag.Relative,
    )

    # TODO: something something anchor?
    pane.title = "Test"

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
