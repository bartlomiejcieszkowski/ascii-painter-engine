import dataclasses
import logging
from typing import Tuple, Union

from retui import _APP_THEME, TerminalWidget, Theme
from retui.base import Rectangle, TerminalColor, json_convert
from retui.default_themes import ThemePoint
from retui.defaults import default_value
from retui.enums import DimensionsFlag, Dock, TextAlign, WordWrap
from retui.input_handling import KeyEvent, MouseEvent, VirtualKeyCodes
from retui.mapping import official_widget

_log = logging.getLogger(__name__)


class Text:
    """
    This class abstracts text
    """

    def __init__(
        self,
        text: str = "",
        text_align: TextAlign = default_value("text_align"),
        text_wrap: WordWrap = default_value("text_wrap"),
    ):
        self.text = text
        self.text_align = text_align
        self.text_wrap = text_wrap
        self.word_wrap_fun = Text.get_word_wrap_function(text_wrap)
        self.text_align_fun = Text.get_text_align_function(text_align)
        self.width = -1
        self.height = -1
        self.lines = []
        self.empty_line = ""
        self.lines_count = 0
        self.shift = 0

    @staticmethod
    def word_wrap_trim(width: int, line: str):
        return line[:width], None

    @staticmethod
    def word_wrap_wrap(width: int, line: str):
        return line[:width], line[width:]

    @staticmethod
    def word_wrap_word_end(width: int, line: str):
        return line[:width], None

    @staticmethod
    def get_word_wrap_function(word_wrap: WordWrap):
        if word_wrap == WordWrap.Trim:
            return Text.word_wrap_trim
        elif word_wrap == WordWrap.Wrap:
            return Text.word_wrap_wrap
        elif word_wrap == WordWrap.WrapWordEnd:
            return Text.word_wrap_word_end
        else:
            return None

    @staticmethod
    def text_align_left(width: int, line: str):
        return line + (width - len(line)) * " "

    @staticmethod
    def text_align_center(width: int, line: str):
        halfway = width - len(line)
        extra = halfway % 2
        halfway = halfway // 2
        # This can either favor left or right, right now we favor left
        return halfway * " " + line + (halfway + extra) * " "

    @staticmethod
    def text_align_right(width: int, line: str):
        return (width - len(line)) * " " + line

    @staticmethod
    def get_text_align_function(text_align: TextAlign):
        if text_align.is_left():
            return Text.text_align_left
        elif text_align.is_center():
            return Text.text_align_center
        elif text_align.is_right():
            return Text.text_align_right
        else:
            return None

    def prepare_lines(self, width: int, height: int):
        if self.dimensions_match(width, height):
            return

        lines = self.text.splitlines(keepends=False)
        self.lines.clear()
        self.empty_line = " " * width
        leftover = None
        while lines or leftover:
            if leftover:
                line = leftover
                leftover = None
            else:
                line = lines.pop(0)
            if len(line) < width:
                nice_line = self.text_align_fun(width, line)
                pass
            else:
                nice_line, leftover = self.word_wrap_fun(width, line)
            if leftover and len(leftover) == 0:
                leftover = None

            self.lines.append(nice_line)

        # Top, bottom, middle
        self.lines_count = len(self.lines)
        self.shift = 0

        if self.lines_count < height:
            if self.text_align.is_top():
                pass
            elif self.text_align.is_middle():
                # e.g 3 lines, 8 height = 3, zero indexing - so we need 2
                self.shift = (height // 2) - ((self.lines_count - 1) // 2) - (height % 2)
            elif self.text_align.is_bottom():
                # e.g. 3 lines, 8 height = 5
                self.shift = height - self.lines_count

        self.width = width
        self.height = height

    def dimensions_match(self, width: int, height: int):
        return self.width == width and self.height == height

    def get_line(self, idx):
        return (
            self.empty_line
            if idx < self.shift or idx >= (self.lines_count + self.shift)
            else self.lines[idx - self.shift]
        )


@official_widget
class BorderWidget(TerminalWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            identifier=kwargs.pop("id", None),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            dock=json_convert("dock", kwargs.pop("dock", None)),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            tab_index=kwargs.pop("tab_index", default_value("tab_index")),
            borderless=kwargs.pop("borderless", False),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            soft_border=kwargs.pop("soft_border", default_value("soft_border")),
            title=kwargs.pop("title", ""),
        )

    def __init__(
        self,
        app,
        identifier: Union[str, None] = None,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        dock: Dock = default_value("dock"),
        dimensions: DimensionsFlag = default_value("dimensions"),
        tab_index: int = default_value("tab_index"),
        borderless: bool = False,
        border_str=None,
        border_color=None,
        soft_border=default_value("soft_border"),
        title="",
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            dock=dock,
            dimensions=dimensions,
            tab_index=tab_index,
        )
        self.soft_border = soft_border
        self.borderless = borderless
        self.title = title
        self.border = None
        self._text = None

        self._inner_dimensions = Rectangle()
        self.docked_dimensions = Rectangle()

        if border_str:
            self.border_from_str(border_str)
        if border_color:
            if not isinstance(border_color, TerminalColor):
                raise Exception(f"border_color needs to be of type {TerminalColor}, got {type(border_color)}")
            self.set_color(border_color)
        # None implies use theme

    def update_dimensions(self):
        super().update_dimensions()

        self._inner_dimensions = self.calculate_inner_dimensions()
        self.docked_dimensions = dataclasses.replace(self._inner_dimensions)

    def calculate_inner_dimensions(self):
        if self.soft_border or self.borderless:
            return self.last_dimensions

        inner = dataclasses.replace(self.last_dimensions)
        inner.x += 1
        inner.y += 1
        inner.width -= 2
        inner.height -= 2
        return inner

    def inner_dimensions(self, docked=True):
        return self.docked_dimensions if docked else self._inner_dimensions

    def border_from_str(self, border_str: str):
        self.border = Theme.border_from_str(border_str)

    def set_color(self, color):
        for i in range(0, 9):
            self.border[i].color = color

    def border_inside_set_color(self, color):
        self.border[ThemePoint.MIDDLE].color = color

    def border_get_point(self, idx: int):
        return self.border[idx] if self.border else _APP_THEME.border[idx]

    def border_get_top(self, width_middle, title):
        if title is None:
            title = ""
        top_left = self.border_get_point(ThemePoint.TOP_LEFT)
        top_right = self.border_get_point(ThemePoint.TOP_RIGHT)
        top = self.border_get_point(ThemePoint.TOP)
        return (
            self.app.brush.color(top_left.color)
            + top_left.c
            + self.app.brush.color(top.color)
            + ((title[: width_middle - 2] + "..") if len(title) > width_middle else title)
            + (top.c * (width_middle - len(self.title)))
            + self.app.brush.color(top_right.color)
            + top_right.c
            + self.app.brush.reset_color()
        )

    def border_get_bottom(self, width_middle):
        bottom_left = self.border_get_point(ThemePoint.BOTTOM_LEFT)
        bottom_right = self.border_get_point(ThemePoint.BOTTOM_RIGHT)
        bottom = self.border_get_point(ThemePoint.BOTTOM)
        return (
            self.app.brush.color(bottom_left.color)
            + bottom_left.c
            + self.app.brush.color(bottom.color)
            + (bottom.c * width_middle)
            + self.app.brush.color(bottom_right.color)
            + bottom_right.c
            + self.app.brush.reset_color()
        )

    def draw(self, force: bool = False):
        if force or self._redraw:
            self._draw_bordered(inside_text=self._text, title=self.title)
            super().draw(force=force)

    def _draw_bordered(self, inside_text: Text = None, title: str = ""):
        y = self.last_dimensions.y
        x = self.last_dimensions.x
        width = self.last_dimensions.width
        height = self.last_dimensions.height
        width_inner = width
        if self.borderless is False:
            width_inner -= 2
        self.app.brush.move_cursor(row=y)
        offset_str = self.app.brush.str_right(x)

        # Top border
        if self.borderless is False:
            self.app.brush.print(offset_str + self.border_get_top(width_inner, title), end="")

        start = 0 if self.borderless else 1
        end = height if self.borderless else (height - 1)
        height_inner = end - start

        if inside_text:
            inside_text.prepare_lines(width=width_inner, height=height_inner)

        inside_border = self.border_get_point(ThemePoint.MIDDLE)
        left_border = None if self.borderless else self.border_get_point(ThemePoint.LEFT)
        right_border = None if self.borderless else self.border_get_point(ThemePoint.RIGHT)
        empty_line = inside_border.c * width_inner

        # Middle part
        for h in range(0, height_inner):
            self.app.brush.move_cursor(row=(y + start + h))
            text = inside_text.get_line(h) if inside_text else empty_line
            leftover = width_inner - len(text)
            line = offset_str

            if self.borderless is False:
                line += self.app.brush.color(left_border.color) + left_border.c

            line += self.app.brush.color(inside_border.color) + text[:width_inner] + (inside_border.c * leftover)

            if self.borderless is False:
                line += self.app.brush.color(right_border.color) + right_border.c

            line += self.app.brush.reset_color()
            self.app.brush.print(line, end="")

        # Bottom border
        if self.borderless is False:
            self.app.brush.move_cursor(row=y + height - 1)
            self.app.brush.print(offset_str + self.border_get_bottom(width_inner), end="\n")
        pass

    def local_point(self, point: Tuple[int, int]) -> Union[Tuple[int, int], Tuple[None, None]]:
        # NOTE: this won't return point if we touch border
        border = 0 if self.borderless else 1
        y = self.last_dimensions.y + border
        x = self.last_dimensions.x + border
        width = self.last_dimensions.width - (border * 2)
        height = self.last_dimensions.height - (border * 2)

        local_x = point[0] - x
        local_y = point[1] - y

        if local_x < 0 or local_x >= width or local_y < 0 or local_y >= height:
            return None, None

        # x, y
        return local_x, local_y


@official_widget
class TextBox(BorderWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            identifier=kwargs.pop("id", None),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            dock=json_convert("dock", kwargs.pop("dock", default_value("dock"))),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            tab_index=kwargs.pop("tab_index", default_value("tab_index")),
            borderless=kwargs.pop("borderless", False),
            text=kwargs.pop("text", ""),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            soft_border=kwargs.pop("soft_border", default_value("soft_border")),
            title=kwargs.pop("title", ""),
            text_align=json_convert("text_align", kwargs.pop("text_align", None)),
            text_wrap=json_convert("text_wrap", kwargs.pop("text_wrap", None)),
        )

    def __init__(
        self,
        app,
        identifier: Union[str, None] = None,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        dock: Dock = default_value("dock"),
        dimensions: DimensionsFlag = default_value("dimensions"),
        tab_index: int = default_value("tab_index"),
        borderless: bool = False,
        text: str = "",
        border_str=None,
        border_color=None,
        soft_border=default_value("soft_border"),
        title="",
        text_align: TextAlign = default_value("text_align"),
        text_wrap: WordWrap = default_value("text_wrap"),
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            dock=dock,
            dimensions=dimensions,
            tab_index=tab_index,
            borderless=borderless,
            border_str=border_str,
            border_color=border_color,
            soft_border=soft_border,
            title=title,
        )
        self._text = Text(text=text, text_align=text_align, text_wrap=text_wrap)
        self.text_align = text_align
        self.text_wrap = text_wrap

    @property
    def text(self):
        return self._text.text

    @text.setter
    def text(self, new_text):
        self._text = Text(text=new_text, text_align=self.text_align, text_wrap=self.text_wrap)

    def draw(self, force: bool = False):
        if force or self._redraw:
            super().draw(force=force)


@official_widget
class Pane(BorderWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            identifier=kwargs.pop("id", None),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            dock=json_convert("dock", kwargs.pop("dock", None)),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            borderless=kwargs.pop("borderless", False),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            soft_border=kwargs.pop("soft_border", default_value("soft_border")),
            title=kwargs.pop("title", ""),
        )

    def __init__(
        self,
        app,
        identifier: Union[str, None] = None,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        dock: Dock = default_value("dock"),
        dimensions: DimensionsFlag = default_value("dimensions"),
        borderless: bool = False,
        border_str=None,
        border_color=None,
        soft_border=default_value("soft_border"),
        title="",
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            dock=dock,
            dimensions=dimensions,
            borderless=borderless,
            border_str=border_str,
            border_color=border_color,
            soft_border=soft_border,
            title=title,
        )
        self.widgets = []

    def draw(self, force: bool = False):
        if force or self._redraw:
            super().draw(force=force)
            for widget in self.widgets:
                widget.draw()

    def dock_add(self, dock: Dock, dimensions: Rectangle) -> bool:
        if dock is Dock.TOP:
            self.docked_dimensions.y += dimensions.height
            self.docked_dimensions.height -= dimensions.height
        elif dock is Dock.BOTTOM:
            self.docked_dimensions.height -= dimensions.height
        elif dock is Dock.LEFT:
            self.docked_dimensions.x += dimensions.width
            self.docked_dimensions.width -= dimensions.width
        elif dock is Dock.RIGHT:
            self.docked_dimensions.width -= dimensions.width

        return not self.docked_dimensions.negative()

    def add_widget(self, widget):
        # TODO widget should take offset from parent
        # right now we will adjust it when adding
        # +1 to account for border
        # TODO: fit check
        widget.parent = self
        self.widgets.append(widget)

    def update_dimensions(self):
        super().update_dimensions()

        for widget in self.widgets:
            widget.update_dimensions()

    def get_widget(self, column: int, row: int) -> Union[TerminalWidget, None]:
        for idx in range(len(self.widgets) - 1, -1, -1):
            widget = self.widgets[idx].get_widget(column, row)
            if widget:
                return widget

        return super().get_widget(column, row)

    def get_widget_by_id(self, identifier: str) -> Union["TerminalWidget", None]:
        widget = super().get_widget_by_id(identifier)
        if widget:
            return widget

        for idx in range(0, len(self.widgets)):
            widget = self.widgets[idx].get_widget_by_id(identifier)
            if widget:
                return widget

        return None


@official_widget
class Button(TextBox):
    def __init__(
        self,
        app,
        x: int,
        y: int,
        width: int,
        height: int,
        dock: Dock,
        dimensions: DimensionsFlag = default_value("dimensions"),
        tab_index: int = default_value("tab_index"),
        borderless: bool = False,
        text: str = "",
        border_str=None,
        border_color=None,
        click_handler=None,
        text_align=TextAlign.MiddleCenter,
    ):
        """
        Init function
        :param app:
        :param x:
        :param y:
        :param width:
        :param height:
        :param dock:
        :param dimensions:
        :param tab_index:
        :param borderless:
        :param text:
        :param border_str:
        :param border_color:
        :param click_handler: function signature should be def click_handler(this: Button) -> bool:
         where return value is True if handled
        """
        super().__init__(
            app=app,
            x=x,
            y=y,
            width=width,
            height=height,
            dock=dock,
            dimensions=dimensions,
            tab_index=tab_index,
            borderless=borderless,
            text=text,
            border_str=border_str,
            border_color=border_color,
            title="",
            text_align=text_align,
        )
        if click_handler is not None and not callable(click_handler):
            raise Exception(
                f"click_handler needs to be callable! click_handler: {click_handler}, type({click_handler})"
            )
        self.click_handler = click_handler

    @staticmethod
    def is_click(event):
        if isinstance(event, MouseEvent):
            if event.button in [event.button.LMB] and event.pressed:
                return True
        elif isinstance(event, KeyEvent):
            if event.vk_code in [VirtualKeyCodes.VK_RETURN, VirtualKeyCodes.VK_SPACE]:
                return True
        return False

    def handle(self, event):
        # TODO shortcut alt+letter? Like on buttons "_O_k" and alt+o presses it
        if self.click_handler and self.is_click(event):
            return self.click_handler(this=self)


@official_widget
class WriteBox(TextBox):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            identifier=kwargs.pop("id", None),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            dock=json_convert("dock", kwargs.pop("dock", None)),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            tab_index=kwargs.pop("tab_index", default_value("tab_index")),
            borderless=kwargs.pop("borderless", False),
            text=kwargs.pop("text", ""),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            title=kwargs.pop("title", ""),
        )

    def __init__(
        self,
        app,
        identifier: Union[str, None] = None,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        dock: Dock = default_value("dock"),
        dimensions: DimensionsFlag = default_value("dimensions"),
        tab_index: int = default_value("tab_index"),
        borderless: bool = False,
        text: str = "",
        border_str=None,
        border_color=None,
        title="",
    ):
        """
        Init function
        :param app:
        :param x:
        :param y:
        :param width:
        :param height:
        :param dock:
        :param dimensions:
        :param tab_index:
        :param borderless:
        :param text:
        :param border_str:
        :param border_color:
        :param click_handler: function signature should be def click_handler(this: Button) -> bool:
         where return value is True if handled
        """
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            dock=dock,
            dimensions=dimensions,
            tab_index=tab_index,
            borderless=borderless,
            text=text,
            border_str=border_str,
            border_color=border_color,
            title=title,
            text_align=default_value("text_align"),
        )

    def write(self, text, append: bool = True):
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        if append:
            self.text += text
        else:
            self.text = text

    def clear(self):
        self.text = ""


@official_widget
class HorizontalLine(BorderWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            identifier=kwargs.pop("id", None),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            dock=json_convert("dock", kwargs.pop("dock", default_value("dock"))),
            dimensions=DimensionsFlag.FillWidth,
            tab_index=kwargs.pop("tab_index", default_value("tab_index")),
            borderless=kwargs.pop("borderless", False),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            soft_border=kwargs.pop("soft_border", default_value("soft_border")),
            title=kwargs.pop("title", ""),
            text_align=json_convert("text_align", kwargs.pop("text_align", None)),
            text_wrap=json_convert("text_wrap", kwargs.pop("text_wrap", None)),
        )

    def __init__(
        self,
        app,
        identifier: Union[str, None] = None,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        dock: Dock = default_value("dock"),
        dimensions: DimensionsFlag = DimensionsFlag.FillWidth,
        tab_index: int = default_value("tab_index"),
        borderless: bool = False,
        text: str = "",
        border_str=None,
        border_color=None,
        soft_border=default_value("soft_border"),
        title="",
        text_align: TextAlign = default_value("text_align"),
        text_wrap: WordWrap = default_value("text_wrap"),
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            dock=dock,
            dimensions=dimensions,
            tab_index=tab_index,
            borderless=borderless,
            border_str=border_str,
            border_color=border_color,
            soft_border=soft_border,
            title=title,
        )
        self._text = Text(text=text, text_align=text_align, text_wrap=text_wrap)
        self.text_align = text_align
        self.text_wrap = text_wrap

    @property
    def text(self):
        return self._text.text

    @text.setter
    def text(self, new_text):
        self._text = Text(text=new_text, text_align=self.text_align, text_wrap=self.text_wrap)

    def draw(self, force: bool = False):
        if force or self._redraw:
            super().draw(force=force)
