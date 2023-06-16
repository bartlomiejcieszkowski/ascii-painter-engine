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
            alignment=ape.Alignment.LeftTop,
            dimensions=ape.DimensionsFlag.Fill,
            text='The pane has 80 width and height. But has "Fill" so it should fill the screen and '
            "ignore dimensions.",
        )
    )

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
