import retui
from retui.enums import DimensionsFlag, Dock, TextAlign
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
            dock=Dock.TOP,
            dimensions=DimensionsFlag.RELATIVE,
        )
    )

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=Dock.BOTTOM,
            dimensions=DimensionsFlag.RELATIVE,
        )
    )

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=Dock.LEFT,
            dimensions=DimensionsFlag.RELATIVE,
        )
    )

    app.add_widget(
        Pane(
            app=app,
            height=10,
            width=10,
            dock=Dock.RIGHT,
            dimensions=DimensionsFlag.RELATIVE,
        )
    )

    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=12,
        width=31,
        dock=Dock.FILL,
        dimensions=DimensionsFlag.FILL,
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
            dock=Dock.FILL,
            dimensions=DimensionsFlag.FILL,
            text="The pane is surrounded by 10% panes and has 'FILL'.\n"
            "So it should be nicely centered\n"
            "Text alignment is Middle Right\n",
            text_align=TextAlign.MIDDLE_RIGHT,
        )
    )

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
