import ascii_painter_engine as ape
from ascii_painter_engine.widget import Pane, TextBox


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = ape.App(log=ape.log.log)
    app.title = title
    app.color_mode()

    pane = Pane(
        app=app,
        x=0,
        y=0,
        height=80,
        width=80,
        alignment=ape.Alignment.Center,
        dimensions=ape.DimensionsFlag.Fill,
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
            alignment=ape.Alignment.TopLeft,
            dimensions=ape.DimensionsFlag.Fill,
            text="The pane has 80 width and height.\nBut has 'Fill' so it should fill the screen and "
            "ignore dimensions.\n012345678911234567892123456789312345678941234567895123456789\n",
        )
    )

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
