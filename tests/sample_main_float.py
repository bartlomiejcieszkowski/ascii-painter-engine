import ascii_painter_engine as ape
from ascii_painter_engine.widget import TextBox, Pane


def test(handle_sigint=True, demo_time_s=None):
    app = ape.App(log=ape.log.log)
    app.title = "sample_main_float.py"
    app.color_mode()

    pane = Pane(app=app, x=0, y=1, height=80, width=100, alignment=ape.Alignment.LeftTop)
    pane.title = 'Test'

    widget = TextBox(app=app, x=0, y=0, height=20, width=40, alignment=ape.Alignment.FloatLeftTop)
    widget.text = '1st float'
    pane.add_widget(widget)

    # pane inside:
    # 1111
    # 1111
    #
    #

    widget = TextBox(app=app, x=0, y=0, height=30, width=60, alignment=ape.Alignment.FloatLeftTop)
    widget.text = '2nd float'
    pane.add_widget(widget)

    # pane inside:
    # 1111222222
    # 1111222222
    #     222222
    #

    widget = TextBox(app=app, x=0, y=0, height=20, width=30, alignment=ape.Alignment.FloatLeftTop)
    widget.text = '3rd float'
    pane.add_widget(widget)

    # pane inside:
    # 1111222222
    # 1111222222
    # 333 222222
    # 333

    app.add_widget(pane)

    app.handle_sigint = handle_sigint
    app.demo_mode(demo_time_s)

    app.run()
