import retui
from retui.widgets import Pane, TextBox


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App()
    app.title = title
    app.color_mode()

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=retui.Dock.TOP,
            dimensions=retui.DimensionsFlag.Relative,
        )
    )

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=retui.Dock.BOTTOM,
            dimensions=retui.DimensionsFlag.Relative,
        )
    )

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=retui.Dock.LEFT,
            dimensions=retui.DimensionsFlag.Relative,
        )
    )

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=retui.Dock.RIGHT,
            dimensions=retui.DimensionsFlag.Relative,
        )
    )

    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=12,
        width=31,
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
            height=4,
            width=20,
            dock=retui.Dock.FILL,
            dimensions=retui.DimensionsFlag.Fill,
            text="The pane is surrounded by 10% panes and has 'FILL'.\n"
            "So it should be nicely centered\n"
            "Text alignment is Middle Right\n",
            text_align=retui.TextAlign.MiddleRight,
        )
    )

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
