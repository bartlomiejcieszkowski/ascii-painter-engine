from typing import Tuple, Union

from ascii_painter_engine import (
    APP_THEME,
    Alignment,
    ConsoleColor,
    ConsoleWidget,
    DimensionsFlag,
    Point,
    TabIndex,
)


class BorderWidget(ConsoleWidget):
    # TODO Border from str
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            alignment=kwargs.pop("alignment", None),
            dimensions=kwargs.pop("dimensions", "Absolute"),
            tab_index=kwargs.pop("tab_index", TabIndex.TAB_INDEX_NOT_SELECTABLE),
            borderless=kwargs.pop("borderless", False),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            title=kwargs.pop("title", ""),
        )

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
        border_str=None,
        border_color=None,
        title="",
    ):
        super().__init__(
            app=app,
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

    def draw_bordered(self, inside_text: str = "", title: str = "", text_wrap: bool = True):
        offset_rows = self.last_dimensions.row
        offset_cols = self.last_dimensions.column
        width = self.last_dimensions.width
        height = self.last_dimensions.height
        width_inner = width
        if self.borderless is False:
            width_inner -= 2
        self.app.brush.MoveCursor(row=offset_rows)
        offset_str = self.app.brush.MoveRight(offset_cols)
        if self.borderless is False:
            self.app.brush.print(offset_str + self.border_get_top(width_inner, title), end="")

        start = 0 if self.borderless else 1
        end = height if self.borderless else (height - 1)

        # prepare text
        text_lines = inside_text.splitlines(keepends=False)
        if text_wrap:
            wrapped_text_lines = []
            # if goes past width, create new line and move it to next one
            for line in text_lines:
                while len(line) > width_inner:
                    # split
                    wrapped_text_lines.append(line[:width_inner])
                    line = line[width_inner:]
                wrapped_text_lines.append(line)
            text_lines = wrapped_text_lines

        for h in range(start, end):
            self.app.brush.MoveCursor(row=offset_rows + h)
            if len(text_lines) > 0:
                text = text_lines.pop(0)
            else:
                text = ""
            leftover = width_inner - len(text)
            line = offset_str

            if self.borderless is False:
                left_border = self.border_get_point(6)
                line += self.app.brush.FgBgColor(left_border.color) + left_border.c

            inside_border = self.border_get_point(0)
            line += self.app.brush.FgBgColor(inside_border.color) + text[:width_inner] + (inside_border.c * leftover)

            if self.borderless is False:
                right_border = self.border_get_point(7)
                line += self.app.brush.FgBgColor(right_border.color) + right_border.c

            line += self.app.brush.ResetColor()
            self.app.brush.print(line, end="")

        if self.borderless is False:
            self.app.brush.MoveCursor(row=offset_rows + height - 1)
            self.app.brush.print(offset_str + self.border_get_bottom(width_inner), end="\n")
        pass

    def local_point(self, point: Tuple[int, int]) -> Tuple[int, int]:
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
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            alignment=kwargs.pop("alignment", None),
            dimensions=kwargs.pop("dimensions", "Absolute"),
            tab_index=kwargs.pop("tab_index", TabIndex.TAB_INDEX_NOT_SELECTABLE),
            borderless=kwargs.pop("borderless", False),
            text=kwargs.pop("text", ""),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            title=kwargs.pop("title", ""),
        )

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
        title="",
    ):
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
            border_str=border_str,
            border_color=border_color,
            title=title,
        )
        self.text = text

    def draw(self):
        return self.draw_bordered(inside_text=self.text, title=self.title)


class Pane(BorderWidget):
    @classmethod
    def from_dict(cls, **kwargs):
        return cls(
            app=kwargs.pop("app"),
            x=kwargs.pop("x"),
            y=kwargs.pop("y"),
            width=kwargs.pop("width"),
            height=kwargs.pop("height"),
            alignment=kwargs.pop("alignment", None),
            dimensions=kwargs.pop("dimensions", "Absolute"),
            borderless=kwargs.pop("borderless", False),
            border_str=kwargs.pop("border_str", None),
            border_color=kwargs.pop("border_color", None),
            title=kwargs.pop("title", ""),
        )

    def __init__(
        self,
        app,
        x: int,
        y: int,
        width: int,
        height: int,
        alignment: Alignment,
        dimensions: DimensionsFlag = DimensionsFlag.Absolute,
        borderless: bool = False,
        border_str=None,
        border_color=None,
        title="",
    ):
        super().__init__(
            app=app,
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
        self.draw_bordered(inside_text="", title=self.title)
        for widget in self.widgets:
            widget.draw()

        pass

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


class Button(TextBox):
    def __init__(self):
        # TODO: distinct border

        pass
