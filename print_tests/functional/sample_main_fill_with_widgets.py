import retui
from retui.enums import DimensionsFlag, Dock, TextAlign
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
            height=10,
            width=20,
            dock=Dock.BOTTOM,
            dimensions=DimensionsFlag.FILL_WIDTH,
            text="The pane has 10 height.\nAnd is docked to BOTTOM so it should"
            " create nice bar at bottom.\nText alignment is Middle Right\n",
            text_align=TextAlign.MIDDLE_CENTER,
        )
    )

    pane.add_widget(
        TextBox(
            app=app,
            x=0,
            y=0,
            height=4,
            width=20,
            dock=Dock.RIGHT,
            dimensions=DimensionsFlag.ABSOLUTE,
            text="The pane has 20 width.\nIt is docked to the RIGHT so"
            "so this should go above bottom bar.\nText alignment is Middle Right\n",
            text_align=TextAlign.MIDDLE_RIGHT,
        )
    )

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
