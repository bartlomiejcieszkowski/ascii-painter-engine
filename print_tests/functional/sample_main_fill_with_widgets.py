import retui
from retui.widgets import Pane, TextBox


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App()
    app.title = title
    app.color_mode()

    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=80,
        width=80,
        dock=retui.Dock.FILL,
        dimensions=retui.DimensionsFlag.Fill,
    )
    # dimensions should be ignored for Fill
    pane.title = "Test"

    pane.add_widget(
        TextBox(
            app=app,
            x=0,
            y=0,
            height=10,
            width=20,
            dock=retui.Dock.BOTTOM,
            dimensions=retui.DimensionsFlag.FillWidth,
            text="The pane has 10 height.\nAnd is docked to BOTTOM so it should"
            " create nice bar at bottom.\nText alignment is Middle Right\n",
            text_align=retui.TextAlign.MiddleRight,
        )
    )

    pane.add_widget(
        TextBox(
            app=app,
            x=0,
            y=0,
            height=4,
            width=20,
            dock=retui.Dock.RIGHT,
            dimensions=retui.DimensionsFlag.Absolute,
            text="The pane has 20 width.\nIt is docked to the RIGHT so"
            "so this should go above bottom bar.\nText alignment is Middle Right\n",
            text_align=retui.TextAlign.MiddleRight,
        )
    )

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
