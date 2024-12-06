import dataclasses
from dataclasses import dataclass

from retui import DefaultThemes
from retui.base import Color, ColorBits, Rectangle, TerminalColor
from retui.default_themes import DefaultThemesType
from retui.enums import Dock, TextAlign
from retui.widgets import Pane, TextBox


@dataclass
class MockApp:
    dimensions: Rectangle
    widgets: list
    docked_dimensions: Rectangle = None
    last_dimensions: Rectangle = None
    dock: Dock = Dock.FILL

    def dock_add(self, dock: Dock, dimensions: Rectangle) -> bool:
        return True

    def add_widget(self, widget):
        widget.parent = self
        self.widgets.append(widget)

    def update_dimensions(self):
        self.last_dimensions = self.dimensions_copy(last=False)
        self.docked_dimensions = self.dimensions_copy(last=True)
        for widget in self.widgets:
            widget.update_dimensions()

    def dimensions_copy(self, last: bool):
        """
        Creates shallow copy of dimensions
        """
        return dataclasses.replace(self.last_dimensions if last else self.dimensions)

    def inner_dimensions(self, docked: bool) -> Rectangle:
        if docked:
            return self.docked_dimensions
        return self.dimensions


def pretty_print(this):
    if type(this) is MockApp:
        print(this)
        return

    print(f"{type(this)}(dimensions={this.dimensions}, dock={this.dock}), last_dimensions={this.last_dimensions}")


def child_print(parent):
    pretty_print(parent)
    if hasattr(parent, "widgets"):
        for widget in parent.widgets:
            child_print(widget)


def test_top_dock():
    app = MockApp(dimensions=Rectangle(0, 0, 100, 100), widgets=[])

    # app.dimensions = Rectangle(0,0,100,100)

    widget = Pane(app=app, dock=Dock.FILL)

    child_widget = Pane(app=app, x=0, y=0, height=20, width=20, dock=Dock.TOP)
    widget.add_widget(child_widget)

    app.add_widget(widget)

    app.update_dimensions()

    child_print(app)
    assert True


def test_sample_main(handle_sigint=True, demo_time_s=None, title=None):
    app = MockApp(dimensions=Rectangle(0, 0, 100, 100), widgets=[])

    widget = TextBox(app=app, x=0, y=0, height=4, width=20, dock=Dock.NONE)
    widget.text = "Test"
    app.add_widget(widget)

    widget = Pane(app=app, x=2, y=8, height=4, width=8, dock=Dock.NONE)
    widget.title = "Little Pane"
    app.add_widget(widget)

    pane = Pane(app=app, x=11, y=8, height=5, width=40, dock=Dock.NONE)
    pane.title = "Bigger Pane"
    app.add_widget(pane)

    test_color = TerminalColor(Color(13, ColorBits.BIT_8), Color(7, ColorBits.BIT_8))

    widget = TextBox(app=app, x=0, y=0, height=3, width=10, dock=Dock.NONE, text_align=TextAlign.BOTTOM_RIGHT)
    widget.text = "Sample text in pane"
    widget.border_from_str(DefaultThemes.get_theme_border_str(DefaultThemesType.DOUBLE_TOP))
    widget.set_color(test_color)
    pane.add_widget(widget)

    widget = TextBox(
        app=app,
        x=10,
        y=0,
        height=3,
        width=25,
        dock=Dock.NONE,
        text_align=TextAlign.BOTTOM_RIGHT,
    )
    widget.text = "TextBox without borders"
    widget.borderless = True
    pane.add_widget(widget)

    app.update_dimensions()
    child_print(app)
