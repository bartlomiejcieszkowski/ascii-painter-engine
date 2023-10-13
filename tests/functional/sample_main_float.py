import retui
from retui.logger import log
from retui.widget import Pane, TextBox


def test(handle_sigint=True, demo_time_s=None, title=None):
    app = retui.App(log=log)
    app.title = title
    app.color_mode()

    pane = Pane(
        app=app,
        x=0,
        y=1,
        height=80,
        width=100,
        alignment=retui.Alignment.TopLeft,
        dimensions=retui.DimensionsFlag.Fill,
    )
    pane.title = "Test"

    widget = TextBox(
        app=app,
        x=0,
        y=0,
        height=20,
        width=40,
        alignment=retui.Alignment.FloatTopLeft,
        dimensions=retui.DimensionsFlag.FillHeightRelativeWidth,
    )
    widget.text = f"1st float {widget}"
    pane.add_widget(widget)

    # pane inside:
    # 1111
    # 1111
    #
    #

    widget = TextBox(
        app=app,
        x=0,
        y=0,
        height=30,
        width=60,
        alignment=retui.Alignment.FloatTopLeft,
        dimensions=retui.DimensionsFlag.FillHeightRelativeWidth,
    )
    widget.text = f"2nd float {widget}"
    pane.add_widget(widget)

    # pane inside:
    # 1111222222
    # 1111222222
    #     222222
    #

    widget = TextBox(
        app=app,
        x=0,
        y=0,
        height=20,
        width=30,
        alignment=retui.Alignment.FloatTopLeft,
        dimensions=retui.DimensionsFlag.FillHeightRelativeWidth,
    )
    widget.text = f"3rd float {widget}"
    pane.add_widget(widget)

    # pane inside:
    # 1111222222
    # 1111222222
    # 333 222222
    # 333
    # FIXME this test is broken - floating windows are not implemented
    # FIXME search for here be dragons
    # FIXME all floating windows stack on top of each other, should be replaced
    # FIXME with nice algorithm that tries to fit them
    # TEXT IS NOT OVERFLOWING, splitting text is fine
    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
