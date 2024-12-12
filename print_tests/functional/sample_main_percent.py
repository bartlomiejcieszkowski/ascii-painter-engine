import retui
import retui.enums
from retui.widgets import Pane


def test(handle_sigint=True, demo_time_s=None, title=None, debug=False) -> int:
    app = retui.App(debug=debug)
    app.title = title
    app.color_mode()

    # TODO: Percent of window, relative
    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=80,
        width=80,
        dock=retui.enums.Dock.NONE,
        dimensions=retui.enums.DimensionsFlag.RELATIVE,
    )

    # TODO: something something anchor?
    pane.title = "Test"

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()

    return 0
