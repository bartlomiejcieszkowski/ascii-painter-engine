import dataclasses
import logging
from abc import ABC
from typing import Tuple, Union

import retui.theme
from retui.base import Rectangle, TerminalColor
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
class TerminalWidget(ABC):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

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
        tab_stop: bool = default_value("tab_stop"),
        scroll_horizontal: bool = default_value("scroll_horizontal"),
        scroll_vertical: bool = default_value("scroll_vertical"),
    ):
        if identifier is None:
            identifier = f"{type(self).__qualname__}_{hash(self):x}"
        # TODO: check if it is unique
        self.identifier = identifier
        self.dimensions = Rectangle(x=x, y=y, width=width, height=height)
        self.dock = dock
        self.app = app
        self.dimensionsFlag = dimensions
        self.parent = None
        self.handlers = {}
        self.tab_index = tab_index
        self.tab_stop = tab_stop
        self.scroll_horizontal = scroll_horizontal
        self.scroll_vertical = scroll_vertical
        # register handlers here
        # when handling click - cache what was there to speed up lookup - invalidate on re-draw
        # iterate in reverse order on widgets - the order on widget list determines Z order
        # - higher idx covers lower one
        self.last_dimensions = Rectangle()

        # internals
        self._redraw = True
        self._update_size = True

    def dimensions_copy(self, last: bool):
        """
        Creates shallow copy of dimensions
        """
        return dataclasses.replace(self.last_dimensions if last else self.dimensions)

    def calculate_dimensions_docked(self):
        dimensions = self.dimensions_copy(last=False)
        parent_docked = self.parent.inner_dimensions(docked=True)
        parent_inner = self.parent.inner_dimensions(docked=False)

        if DimensionsFlag.RelativeHeight in self.dimensionsFlag and self.dock in [Dock.BOTTOM, Dock.TOP]:
            dimensions.height = (dimensions.height * parent_inner.height) // 100
        elif DimensionsFlag.RelativeWidth in self.dimensionsFlag and self.dock in [Dock.LEFT, Dock.RIGHT]:
            dimensions.width = (dimensions.width * parent_inner.width) // 100

        # TODO: check for overflow, if it goes past terminal width it will wrap around at next line

        if self.dock is Dock.FILL:
            dimensions = dataclasses.replace(parent_docked)
        elif self.dock is Dock.TOP:
            dimensions.x = parent_docked.x
            dimensions.y = parent_docked.y
            dimensions.width = parent_docked.width
        elif self.dock is Dock.BOTTOM:
            dimensions.x = parent_docked.x
            dimensions.y = parent_docked.y + parent_docked.height - dimensions.height
            dimensions.width = parent_docked.width
        elif self.dock is Dock.LEFT:
            dimensions.x = parent_docked.x
            dimensions.y = parent_docked.y
            dimensions.height = parent_docked.height
        elif self.dock is Dock.RIGHT:
            dimensions.x = parent_docked.x + parent_docked.width - dimensions.width
            dimensions.y = parent_docked.y
            dimensions.height = parent_docked.height
        else:
            raise Exception(f"Invalid dock {self.dock}")

        # Should this throw failure up? Eg no space? display whole screen - resize screen?
        if not self.parent.dock_add(self.dock, dimensions):
            _log.critical(
                f"Dock size exceeded - fix the widget defintions - "
                f"parent: {self.parent.identifier} - {parent_docked},"
                f"child: {self.identifier} - {dimensions}"
            )
        return dimensions

    def calculate_dimensions(self):
        dimensions = self.dimensions_copy(last=False)
        parent_dimensions = self.parent.inner_dimensions(docked=False)
        if DimensionsFlag.RelativeWidth in self.dimensionsFlag:
            dimensions.width = (dimensions.width * parent_dimensions.width) // 100
        elif DimensionsFlag.FillWidth in self.dimensionsFlag:
            dimensions.width = parent_dimensions.width

        if DimensionsFlag.RelativeHeight in self.dimensionsFlag:
            # concern about rows - 1
            dimensions.height = (dimensions.height * parent_dimensions.height) // 100
        elif DimensionsFlag.FillHeight in self.dimensionsFlag:
            dimensions.height = parent_dimensions.height

        dimensions.translate_coordinates(parent_dimensions)
        return dimensions

    def update_dimensions(self):
        self._update_size = False
        # update dimensions is separate, so we separate drawing logic, so if one implement own widget
        # doesn't have to remember to call update_dimensions every time or do it incorrectly

        if self.dock is not Dock.NONE:
            dimensions = self.calculate_dimensions_docked()
        else:
            dimensions = self.calculate_dimensions()
            # TODO: Not enough FLAGS
            # if Alignment.Left in self.dock:
            #     x += self.parent.inner_x()
            # elif Alignment.Right in self.dock:
            #     x = self.parent.inner_x() + self.parent.inner_width() - width - x
            # if Alignment.Top in self.dock:
            #     y += self.parent.inner_y()
            # elif Alignment.Bottom in self.dock:
            #     y = self.parent.inner_y() + self.parent.inner_height() - height - y

        self.last_dimensions = dimensions
        self._redraw = True

    def dock_add(self, dock: Dock, dimensions: Rectangle) -> bool:
        raise NotImplementedError("You can't dock inside this class")

    def get_widget(self, column: int, row: int) -> Union["TerminalWidget", None]:
        return self if self.contains_point(column, row) else None

    def get_widget_by_id(self, identifier: str) -> Union["TerminalWidget", None]:
        return self if self.identifier == identifier else None

    def handle(self, event):
        # guess we should pass also unknown args
        # raise Exception('handle')
        pass

    def draw(self, force: bool = False):
        self._redraw = False

    def contains_point(self, column: int, row: int):
        return self.last_dimensions.contains_point(column, row)

    def __str__(self):
        return (
            f"[{self.dimensions}"
            f"dock:{self.dock} dimensions:{self.dimensionsFlag} type:{type(self)} 0x{hash(self):X}]"
        )


@official_widget
class BorderWidget(TerminalWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def __init__(
        self,
        borderless: bool = False,
        soft_border: bool = default_value("soft_border"),
        title: str = "",
        border_str=None,
        border_color=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

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
        self.border = retui.theme.Theme.border_from_str(border_str)

    def set_color(self, color):
        for i in range(0, 9):
            self.border[i].color = color

    def border_inside_set_color(self, color):
        self.border[ThemePoint.MIDDLE].color = color

    def border_get_point(self, idx: int):
        return self.border[idx] if self.border else retui.theme._APP_THEME.border[idx]

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
        return cls(**kwargs)

    def __init__(
        self,
        text: str = "",
        text_align: TextAlign = default_value("text_align"),
        text_wrap: WordWrap = default_value("text_wrap"),
        **kwargs,
    ):
        super().__init__(**kwargs)
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
        return cls(**kwargs)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        elif dock is Dock.FILL:
            # all available docked space is consumed
            self.docked_dimensions.update(0, 0, 0, 0)

        return not self.docked_dimensions.negative()

    def add_widget(self, widget):
        # TODO widget should take offset from parent
        # right now we will adjust it when adding
        # +1 to account for border
        # TODO: fit check
        widget.parent = self
        self.widgets.append(widget)

    def add_widget_after(self, widget: TerminalWidget, widget_on_list: TerminalWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError:
            return False

        widget.parent = self
        self.widgets.insert(idx + 1, widget)
        # TODO ut to check if it will fail if the widget is last widget
        return True

    def add_widget_before(self, widget: TerminalWidget, widget_on_list: TerminalWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError:
            return False

        widget.parent = self
        self.widgets.insert(idx, widget)
        return True

    def update_dimensions(self):
        super().update_dimensions()

        for widget in self.widgets:
            widget.update_dimensions()

    def get_widget(self, column: int, row: int) -> Union[TerminalWidget, None]:
        match = super().get_widget(column, row)

        if match:
            # this widget contains point, check child widgets, e.g. button in a pane
            for idx in range(len(self.widgets) - 1, -1, -1):
                widget = self.widgets[idx].get_widget(column, row)
                if widget:
                    return widget

        return match

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
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def __init__(self, click_handler=None, **kwargs):
        """
        Init function
        :param click_handler: function signature should be def click_handler(this: Button) -> bool:
         where return value is True if handled
        :param kwargs see TextBox
        """
        super().__init__(**kwargs)

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
        return cls(**kwargs)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        return cls(**kwargs)

    def __init__(
        self,
        text: str = "",
        text_align: TextAlign = default_value("text_align"),
        text_wrap: WordWrap = default_value("text_wrap"),
        **kwargs,
    ):
        super().__init__(**kwargs)

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
