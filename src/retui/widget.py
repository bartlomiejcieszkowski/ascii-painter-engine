from typing import Tuple, Union

from . import (
    APP_THEME,
    Alignment,
    ConsoleColor,
    ConsoleWidget,
    DimensionsFlag,
    KeyEvent,
    MouseEvent,
    Point,
    TabIndex,
    TextAlign,
    VirtualKeyCodes,
    WordWrap,
    json_convert,
)


class Text:
    """
    This class abstracts text
    """

    def __init__(self, text: str = "", text_align: TextAlign = TextAlign.TopLeft, text_wrap: WordWrap = WordWrap.Wrap):
        # maybe word wrap?
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


class BorderWidget(ConsoleWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            identifier=kwargs.pop("id", None),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            alignment=json_convert("alignment", kwargs.pop("alignment", None)),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            tab_index=kwargs.pop("tab_index", TabIndex.TAB_INDEX_NOT_SELECTABLE),
            borderless=kwargs.pop("borderless", False),
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
        alignment: Alignment = Alignment.TopLeft,
        dimensions: DimensionsFlag = DimensionsFlag.Absolute,
        tab_index: int = TabIndex.TAB_INDEX_NOT_SELECTABLE,
        borderless: bool = False,
        border_str=None,
        border_color=None,
        title="",
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            alignment=alignment,
            dimensions=dimensions,
            tab_index=tab_index,
        )
        self.borderless = borderless
        self.title = title
        self.border = None
        if border_str:
            self.border_from_str(border_str)
        if border_color:
            if type(border_color) is not ConsoleColor:
                raise Exception(f"border_color needs to be of type {ConsoleColor}, got {type(border_color)}")
            self.border_set_color(border_color)
        # None implies use theme

    def inner_x(self):
        if self.borderless:
            return self.last_dimensions.column
        return self.last_dimensions.column + 1

    def inner_y(self):
        if self.borderless:
            return self.last_dimensions.row
        return self.last_dimensions.row + 1

    def inner_width(self):
        if self.borderless:
            return self.last_dimensions.width
        return self.last_dimensions.width - 2

    def inner_height(self):
        if self.borderless:
            return self.last_dimensions.height
        return self.last_dimensions.height - 2

    def border_from_str(self, border_str: str):
        if len(border_str) < 9:
            raise Exception(f"border_str must have at least len of 9 - got {len(border_str)}")
        self.border = []
        for i in range(0, 9):
            self.border.append(Point(border_str[i]))

    def border_set_color(self, color):
        for i in range(1, 9):
            self.border[i].color = color

    def border_inside_set_color(self, color):
        self.border[0].color = color

    def border_get_point(self, idx: int):
        return self.border[idx] if self.border else APP_THEME.border[idx]

    def border_get_top(self, width_middle, title):
        if title is None:
            title = ""
        left_top_corner = self.border_get_point(1)
        right_top_corner = self.border_get_point(2)
        top_border = self.border_get_point(5)
        return (
            self.app.brush.FgBgColor(left_top_corner.color)
            + left_top_corner.c
            + self.app.brush.FgBgColor(top_border.color)
            + ((title[: width_middle - 2] + "..") if len(title) > width_middle else title)
            + (top_border.c * (width_middle - len(self.title)))
            + self.app.brush.FgBgColor(right_top_corner.color)
            + right_top_corner.c
            + self.app.brush.ResetColor()
        )

    def border_get_bottom(self, width_middle):
        left_bottom_corner = self.border_get_point(3)
        right_bottom_corner = self.border_get_point(4)
        bottom_border = self.border_get_point(8)
        return (
            self.app.brush.FgBgColor(left_bottom_corner.color)
            + left_bottom_corner.c
            + self.app.brush.FgBgColor(bottom_border.color)
            + (bottom_border.c * width_middle)
            + self.app.brush.FgBgColor(right_bottom_corner.color)
            + right_bottom_corner.c
            + self.app.brush.ResetColor()
        )

    def draw(self):
        self.draw_bordered(title=self.title)

    def draw_bordered(self, inside_text: Text = None, title: str = ""):
        offset_rows = self.last_dimensions.row
        offset_cols = self.last_dimensions.column
        width = self.last_dimensions.width
        height = self.last_dimensions.height
        width_inner = width
        if self.borderless is False:
            width_inner -= 2
        self.app.brush.MoveCursor(row=offset_rows)
        offset_str = self.app.brush.MoveRight(offset_cols)

        # Top border
        if self.borderless is False:
            self.app.brush.print(offset_str + self.border_get_top(width_inner, title), end="")

        start = 0 if self.borderless else 1
        end = height if self.borderless else (height - 1)
        height_inner = end - start

        if inside_text:
            inside_text.prepare_lines(width=width_inner, height=height_inner)

        inside_border = self.border_get_point(0)
        left_border = None if self.borderless else self.border_get_point(6)
        right_border = None if self.borderless else self.border_get_point(7)
        empty_line = inside_border.c * width_inner

        # Middle part
        for h in range(0, height_inner):
            self.app.brush.MoveCursor(row=(offset_rows + start + h))
            text = inside_text.get_line(h) if inside_text else empty_line
            leftover = width_inner - len(text)
            line = offset_str

            if self.borderless is False:
                line += self.app.brush.FgBgColor(left_border.color) + left_border.c

            line += self.app.brush.FgBgColor(inside_border.color) + text[:width_inner] + (inside_border.c * leftover)

            if self.borderless is False:
                line += self.app.brush.FgBgColor(right_border.color) + right_border.c

            line += self.app.brush.ResetColor()
            self.app.brush.print(line, end="")

        # Bottom border
        if self.borderless is False:
            self.app.brush.MoveCursor(row=offset_rows + height - 1)
            self.app.brush.print(offset_str + self.border_get_bottom(width_inner), end="\n")
        pass

    def local_point(self, point: Tuple[int, int]) -> Union[Tuple[int, int], Tuple[None, None]]:
        # NOTE: this won't return point if we touch border
        border = 0 if self.borderless else 1
        offset_rows = self.last_dimensions.row + border
        offset_cols = self.last_dimensions.column + border
        width = self.last_dimensions.width - (border * 2)
        height = self.last_dimensions.height - (border * 2)

        local_column = point[0] - offset_cols
        local_row = point[1] - offset_rows

        if local_column < 0 or local_column >= width or local_row < 0 or local_row >= height:
            return None, None

        # x, y
        return local_column, local_row


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
            alignment=json_convert("alignment", kwargs.pop("alignment", None)),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            tab_index=kwargs.pop("tab_index", TabIndex.TAB_INDEX_NOT_SELECTABLE),
            borderless=kwargs.pop("borderless", False),
            text=kwargs.pop("text", ""),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
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
        alignment: Alignment = Alignment.TopLeft,
        dimensions: DimensionsFlag = DimensionsFlag.Absolute,
        tab_index: int = TabIndex.TAB_INDEX_NOT_SELECTABLE,
        borderless: bool = False,
        text: str = "",
        border_str=None,
        border_color=None,
        title="",
        text_align: TextAlign = TextAlign.TopLeft,
        text_wrap: WordWrap = WordWrap.Wrap,
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            alignment=alignment,
            dimensions=dimensions,
            tab_index=tab_index,
            borderless=borderless,
            border_str=border_str,
            border_color=border_color,
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

    def draw(self):
        return self.draw_bordered(inside_text=self._text, title=self.title)


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
            alignment=json_convert("alignment", kwargs.pop("alignment", None)),
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", None)),
            borderless=kwargs.pop("borderless", False),
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
        alignment: Alignment = Alignment.TopLeft,
        dimensions: DimensionsFlag = DimensionsFlag.Absolute,
        borderless: bool = False,
        border_str=None,
        border_color=None,
        title="",
    ):
        super().__init__(
            app=app,
            identifier=identifier,
            x=x,
            y=y,
            width=width,
            height=height,
            alignment=alignment,
            dimensions=dimensions,
            borderless=borderless,
            border_str=border_str,
            border_color=border_color,
            title=title,
        )
        self.widgets = []

    def draw(self):
        self.draw_bordered(title=self.title)
        for widget in self.widgets:
            widget.draw()

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

    def get_widget(self, column: int, row: int) -> Union[ConsoleWidget, None]:
        for idx in range(len(self.widgets) - 1, -1, -1):
            widget = self.widgets[idx].get_widget(column, row)
            if widget:
                return widget

        return super().get_widget(column, row)

    def get_widget_by_id(self, identifier: str) -> Union["ConsoleWidget", None]:
        widget = super().get_widget_by_id(identifier)
        if widget:
            return widget

        for idx in range(0, len(self.widgets)):
            widget = self.widgets[idx].get_widget_by_id(identifier)
            if widget:
                return widget

        return None


class Button(TextBox):
    def __init__(
        self,
        app,
        x: int,
        y: int,
        width: int,
        height: int,
        alignment: Alignment,
        dimensions: DimensionsFlag = DimensionsFlag.Absolute,
        tab_index: int = TabIndex.TAB_INDEX_NOT_SELECTABLE,
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
        :param alignment:
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
            alignment=alignment,
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
