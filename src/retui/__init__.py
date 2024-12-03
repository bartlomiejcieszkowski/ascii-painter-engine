"""
Python TUI library
"""

__version__ = "0.1.0"
__author__ = "Bartlomiej Cieszkowski <bartlomiej.cieszkowski@gmail.com>"
__license__ = "MIT"

import asyncio
import concurrent.futures
import dataclasses
import logging
import signal
import sys
import threading
from abc import ABC
from collections import deque
from typing import Union

import retui.input_handling
import retui.terminal
import retui.terminal.base
from retui.base import Color, ColorBits, Point, Rectangle, TerminalColor, json_convert
from retui.default_themes import DefaultThemes
from retui.defaults import default_value
from retui.enums import DimensionsFlag, Dock
from retui.mapping import log_widgets
from retui.theme import Selectors

logging.getLogger(__name__).addHandler(logging.NullHandler())

_log = logging.getLogger(__name__)

# TASK LIST:
# TODO: Percent handling inside Pane - guess will need to add start_x, start_y + width height taken from parent
# TODO: Redraw only when covered - blinking over ssh in tmux - temporary: redraw only on size change
# TODO: trim line to screen width on debug prints
# TODO: Relative dimensions, 1 Top 80 percent, 2nd bottom 20 percent - got 1 free line..

# Notes:
# You can have extra line of console, which won't be fully visible - as w/a just don't use last line
# If new size is greater, then fill with new lines, so we won't be drawing in the middle of screen


def add_window_logger(level: int = logging.DEBUG) -> logging.StreamHandler:
    # TODO move functionality from debug_print here
    pass


class TerminalWidget(ABC):
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
            dimensions=json_convert("dimensions", kwargs.pop("dimensions", default_value("dimensions"))),
            tab_index=kwargs.pop("tab_index", default_value("tab_index")),
            scroll_horizontal=kwargs.pop("scroll_horizontal", default_value("scroll_horizontal")),
            scroll_vertical=kwargs.pop("scroll_vertical", default_value("scroll_vertical")),
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
        self.scroll_horizontal = scroll_horizontal
        self.scroll_vertical = scroll_vertical
        # register handlers here
        # when handling click - cache what was there to speed up lookup - invalidate on re-draw
        # iterate in reverse order on widgets - the order on widget list determines Z order
        # - higher idx covers lower one
        self.last_dimensions = Rectangle(0, 0, 0, 0)

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

        size = 0

        if DimensionsFlag.RelativeHeight in self.dimensionsFlag and self.dock in [Dock.BOTTOM, Dock.TOP]:
            size = dimensions.height = (dimensions.height * parent_inner.height) // 100
        elif DimensionsFlag.RelativeWidth in self.dimensionsFlag and self.dock in [Dock.LEFT, Dock.RIGHT]:
            size = dimensions.width = (dimensions.width * parent_inner.width) // 100

        if self.dock is Dock.FILL:
            dimensions = dataclasses.replace(parent_docked)
        elif self.dock is Dock.TOP:
            dimensions.x = parent_docked.x
            dimensions.y = parent_docked.y
            dimensions.width = parent_docked.width
            # TODO: Docked, with relative height/width, eg. Dock.TOP with 80%
            # TODO: check height? or overflow?
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
        if not self.parent.dock_add(self.dock, size):
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

    def dock_add(self, dock: Dock, size: int) -> bool:
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


class App:
    def __init__(self, title=None, debug: bool = False):
        self.title = title
        self.identifier = "App"

        self.terminal = retui.terminal.get_terminal(self)
        self.widgets = []
        self.brush = Brush(self.terminal.vt_supported)
        self.debug_colors = TerminalColor()
        self.running = False

        self.docked_dimensions = Rectangle()
        self.dimensions = Rectangle()
        self.last_dimensions = Rectangle()
        self.handle_sigint = True

        self.mouse_lmb_state = 0

        self.column_row_widget_cache = {}

        self.demo_thread = None
        self.demo_time_s = None
        self.demo_event = None
        self.emulate_screen_dimensions = None
        self.debug = debug

        self._redraw = True
        self._update_size = True

        # Scrollable attributes
        self.scroll_horizontal = False
        self.scroll_vertical = False

        # asyncio
        self.thread_pool_executor = None
        _log.info("App init done")

    @staticmethod
    def demo_run(app):
        app.demo_event.wait(app.demo_time_s)
        print(f"DEMO MODE - {app.demo_time_s}s - END")
        if app.demo_event.is_set():
            return
        app.running = False

    def init_asyncio(self):
        self.thread_pool_executor = concurrent.futures.ThreadPoolExecutor()

    def register_tasks(self):
        pass

    def dimensions_copy(self, last: bool):
        return dataclasses.replace(self.last_dimensions if last else self.dimensions)

    def inner_dimensions(self, docked: bool) -> Rectangle:
        if docked:
            return self.docked_dimensions
        return self.dimensions

    def dock_add(self, dock: Dock, size: int) -> bool:
        if dock is Dock.TOP:
            self.docked_dimensions.y += size
            self.docked_dimensions.height -= size
        elif dock is Dock.BOTTOM:
            self.docked_dimensions.height -= size
        elif dock is Dock.LEFT:
            self.docked_dimensions.x += size
            self.docked_dimensions.width -= size
        elif dock is Dock.RIGHT:
            self.docked_dimensions.width -= size
        elif dock is Dock.FILL:
            # all available docked space is consumed
            self.docked_dimensions.update(0, 0, 0, 0)

        return not self.docked_dimensions.negative()

    def debug_print(self, text, end="\n", row_off=-1):
        if self.debug:
            _log.debug(text)
            # TODO
            row = (0 if row_off >= 0 else self.terminal.rows) + row_off
            self.brush.move_cursor(row=row)
            print(self.debug_colors)
            self.brush.print(text, end=end, color=self.debug_colors)

    def clear(self, reuse=True):
        self.dimensions.width, self.dimensions.height = self.terminal.update_size()
        if reuse:
            self.brush.move_cursor(0, 0)
        for line in retui.terminal.TerminalBuffer.get_buffer(
            self.terminal.columns, self.terminal.rows, " ", debug=False
        ):
            print(line, end="\n", flush=True)  # TODO: Would it be ok to just flush after for?
        self._update_size = True

    def get_widget(self, column: int, row: int) -> Union[TerminalWidget, None]:
        for idx in range(len(self.widgets) - 1, -1, -1):
            widget = self.widgets[idx].get_widget(column, row)
            if widget:
                return widget
        return None

    def get_widget_by_id(self, identifier) -> Union[TerminalWidget, None]:
        for idx in range(0, len(self.widgets)):
            widget = self.widgets[idx].get_widget_by_id(identifier)
            if widget:
                return widget
        return None

    def handle_click(self, event: retui.input_handling.MouseEvent):
        # naive cache - based on clicked point
        # pro - we can create heat map
        # cons - it would be better with rectangle
        widget = self.column_row_widget_cache.get(event.coordinates, 1)
        if isinstance(widget, int):
            widget = self.get_widget(event.coordinates[0], event.coordinates[1])
            self.column_row_widget_cache[event.coordinates] = widget
        if widget:
            widget.handle(event)

        return widget

    @staticmethod
    def handle_events_callback(ctx, events_list):
        ctx.handle_events(events_list)

    def handle_events(self, events_list):
        off = -2
        col = 0
        # with -1 - 2 lines nearest end of screen overwrite each other
        for event in events_list:
            if isinstance(event, deque):
                self.handle_events(event)
            elif isinstance(event, list):
                self.handle_events(event)
            elif isinstance(event, retui.input_handling.MouseEvent):
                # we could use mask here, but then we will handle holding right button and
                # pressing/releasing left button and other combinations, and frankly I don't want to
                # if (event.button_state & 0x1) == 0x1 and event.event_flags == 0:
                # widget = None
                # if event.button == event.button.LMB:
                #    widget = self.handle_click(event)
                # elif event.button == event.button.RMB:
                #    widget = self.handle_click(event)
                widget = self.handle_click(event)

                self.brush.move_cursor(row=(self.terminal.rows + off) - 1)
                if widget:
                    _log.debug(
                        f"x: {event.coordinates[0]} y: {event.coordinates[1]} "
                        f"button:{event.button} press:{event.pressed} widget:{widget}"
                    )

                self.debug_print(event, row_off=-4)
            elif isinstance(event, retui.terminal.base.SizeChangeEvent):
                self.clear()
                self.debug_print(f"size: {self.terminal.columns:3}x{self.terminal.rows:3}", row_off=-2)
            elif isinstance(event, retui.input_handling.KeyEvent):
                self.debug_print(event, row_off=-3)
            else:
                self.brush.move_cursor(row=(self.terminal.rows + off), column=col)
                debug_string = f'type={type(event)} event="{event}", '
                # col = len(debug_string)
                self.debug_print(debug_string, row_off=-1)
                pass

    signal_sigint_ctx = None

    @staticmethod
    def signal_sigint_handler(signum, frame):
        App.signal_sigint_ctx.signal_sigint()

    def signal_sigint(self):
        self.running = False
        # TODO: read_events is blocking, sos this one needs to be somehow inject, otherwise we wait for first new event
        # works accidentally - as releasing ctrl-c cause key event ;)

    def demo_mode(self, time_s):
        self.demo_time_s = time_s

    def emulate_screen(self, height: int, width: int):
        self.emulate_screen_dimensions = (height, width)

    def draw(self, force: bool = False):
        if force or self._redraw:
            for widget in self.widgets:
                widget.draw(force=force)
            self._redraw = False
        self.brush.move_cursor(row=self.terminal.rows - 1)

    def update_dimensions(self):
        self._update_size = False
        # TODO For APP always use current - is this correct assumption?
        self.docked_dimensions = self.dimensions_copy(last=False)
        self.last_dimensions = self.dimensions_copy(last=False)
        for widget in self.widgets:
            widget.update_dimensions()
        self._redraw = True

    def run(self) -> int:
        if self.running is True:
            return -1

        self.init_asyncio()

        if self.debug:
            log_widgets(_log.debug)

        if self.emulate_screen_dimensions:
            self.terminal.rows = self.emulate_screen_dimensions[0]
            self.terminal.columns = self.emulate_screen_dimensions[1]

        if self.title:
            self.terminal.set_title(self.title)

        if self.handle_sigint:
            App.signal_sigint_ctx = self
            signal.signal(signal.SIGINT, App.signal_sigint_handler)

        if self.demo_time_s and self.demo_time_s > 0:
            self.demo_event = threading.Event()
            self.demo_thread = threading.Thread(target=App.demo_run, args=(self,))
            self.demo_thread.start()
            self.terminal.demo_mode()

        self.running = True

        self.clear(reuse=False)

        self.terminal.interactive_mode()

        self.brush.cursor_hide()
        self.handle_events([retui.terminal.base.SizeChangeEvent()])

        self.register_tasks()

        asyncio.run(self.main_loop())

        if self.demo_thread and self.demo_thread.is_alive():
            self.demo_event.set()
            self.demo_thread.join()

        # Move to the end, so we won't end up writing in middle of screen
        self.brush.move_cursor(self.terminal.rows - 1)
        self.brush.cursor_show()
        self.brush.print(end="\n")
        return 0

    async def main_loop(self):
        while self.running:
            if self._update_size:
                self.column_row_widget_cache.clear()
                self.update_dimensions()
            self.draw()

            # this is blocking
            if not self.terminal.read_events(self.handle_events_callback, self):
                break
        # await asyncio.sleep(0.1)

    def color_mode(self, enable=True) -> bool:
        if enable:
            success = self.terminal.set_color_mode(enable)
            self.brush.color_mode(success)
            if success:
                # self.brush.color_mode(enable)
                self.debug_colors = TerminalColor(Color(14, ColorBits.Bit8), Color(4, ColorBits.Bit8))
        else:
            self.debug_colors = TerminalColor()
            self.brush.color_mode(enable)
            success = self.terminal.set_color_mode(enable)
        return success

    def add_widget(self, widget: TerminalWidget) -> None:
        widget.parent = self
        self.widgets.append(widget)

    def add_widget_after(self, widget: TerminalWidget, widget_on_list: TerminalWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError:
            return False

        widget.parent = self
        self.widgets.insert(idx + 1, widget)
        return True

    def add_widget_before(self, widget: TerminalWidget, widget_on_list: TerminalWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError:
            return False

        widget.parent = self
        self.widgets.insert(idx, widget)
        return True


class Theme:
    class Colors:
        def __init__(self):
            self.text = TerminalColor(Color(0, ColorBits.Bit24))

        @classmethod
        def monokai(cls):
            # cyan = 0x00B9D7
            # gold_brown = 0xABAA98
            # green = 0x82CDB9
            # off_white = 0xF5F5F5
            # orange = 0xF37259
            # pink = 0xFF3D70
            # pink_magenta = 0xF7208B
            # yellow = 0xF9F5C2
            pass

    def __init__(self, border: list[Point]):
        # border string
        # 155552
        # 600007
        # 600007
        # 388884
        # where the string is in form
        # '012345678'

        # validate border
        self.border = []
        if len(border) >= 9:
            for i in range(0, 9):
                if not isinstance(border[i], Point):
                    break
                self.border.append(border[i])

        if len(self.border) < 9:
            # invalid border TODO
            self.border = 9 * [Point(" ")]

        self.selectors = Selectors()

    def set_color(self, color):
        for i in range(0, 9):
            self.border[i].color = color

    def border_inside_set_color(self, color):
        self.border[0].color = color

    @staticmethod
    def border_from_str(border_str: str) -> list[Point]:
        border = []
        if len(border_str) < 9:
            raise Exception(f"border_str must have at least len of 9 - got {len(border_str)}")
        for i in range(0, 9):
            border.append(Point(border_str[i]))
        return border

    @classmethod
    def default_theme(cls):
        return cls(border=_DEFAULT_THEME_BORDER)


_DEFAULT_THEME_BORDER = Theme.border_from_str(DefaultThemes.get_default_theme_border_str())
_APP_THEME = Theme.default_theme()


class Brush:
    def __init__(self, use_color=True):
        self.file = sys.stdout
        self.console_color = TerminalColor()
        self.use_color = use_color
        # TODO: this comes from vt_supported, we override it with color_mode

    RESET = "\x1B[0m"

    def color_mode(self, enable=True):
        self.use_color = enable

    def foreground_color(self, color: Color, check_last=False):
        updated = self.console_color.update_foreground(color)
        if (not updated and check_last) or (self.console_color.foreground is None):
            return ""
        return f"\x1B[38;{int(self.console_color.foreground.bits)};{self.console_color.foreground.color}m"

    def background_color(self, color: Color, check_last=False):
        updated = self.console_color.update_background(color)
        if (not updated and check_last) or (self.console_color.background is None):
            return ""
        return f"\x1B[48;{int(self.console_color.background.bits)};{self.console_color.background.color}m"

    def color(self, console_color: TerminalColor, check_last=False):
        if self.console_color == console_color:
            return ""
        ret_val = self.reset_color()
        ret_val += self.foreground_color(console_color.foreground, check_last)
        ret_val += self.background_color(console_color.background, check_last)
        return ret_val

    def print(self, *args, sep=" ", end="", color: Union[TerminalColor, None] = None):
        # print(f"sep: {sep} end: {end}, color: {color} args: {args}")
        if color is None or color.no_color():
            print(*args, sep=sep, end=end, file=self.file, flush=True)
        else:
            color = self.color(color)
            print(color)
            print(
                color + " ".join(map(str, args)) + self.RESET,
                sep=sep,
                end=end,
                file=self.file,
                flush=True,
            )

    def set_foreground(self, color):
        fg_color = self.foreground_color(color)
        if fg_color != "":
            print(fg_color, end="", file=self.file)

    def set_background(self, color):
        bg_color = self.background_color(color)
        if bg_color != "":
            print(bg_color, end="", file=self.file)

    def reset_color(self):
        self.console_color.reset()
        return self.RESET

    @staticmethod
    def str_up(cells: int = 1):
        return f"\x1B[{cells}A"

    @staticmethod
    def str_down(cells: int = 1):
        return f"\x1B[{cells}B"

    @staticmethod
    def str_right(cells: int = 1) -> str:
        if cells > 0:
            return f"\x1B[{cells}C"
        return ""

    @staticmethod
    def str_left(cells: int = 1) -> str:
        if cells > 0:
            return f"\x1B[{cells}D"
        return ""

    @staticmethod
    def str_line_down(lines: int = 1):
        return f"\x1B[{lines}E"  # not ANSI.SYS

    @staticmethod
    def str_line_up(lines: int = 1):
        return f"\x1B[{lines}F"  # not ANSI.SYS

    @staticmethod
    def str_column_absolute(column: int = 1):
        return f"\x1B[{column}G"  # not ANSI.SYS

    def move_cursor(self, row: int = 0, column: int = 0):
        # 0-based to 1-based
        print(f"\x1B[{row + 1};{column + 1}H", end="", file=self.file)

    def horizontal_vertical_position(self, row: int = 0, column: int = 0):
        # 0-based to 1-based
        print(f"\x1B[{row + 1};{column + 1}f", end="", file=self.file)

    def cursor_hide(self):
        print("\x1b[?25l", end="", file=self.file)
        # alternative on windows without vt - call to SetConsoleCursorInfo:
        # https://docs.microsoft.com/en-us/windows/console/setconsolecursorinfo?redirectedfrom=MSDN

    def cursor_show(self):
        print("\x1b[?25h", end="", file=self.file)


class Test:
    @staticmethod
    def color_line(start, end, text="  ", use_color=False, width=2):
        for color in range(start, end):
            print(
                f'\x1B[48;5;{color}m{("{:" + str(width) + "}").format(color) if use_color else text}',
                end="",
            )
        print("\x1B[0m")

    @staticmethod
    def color_line_24bit(start, end, step=0):
        for color in range(start, end, step):
            print(f"\x1B[48;2;{color};{color};{color}mXD", end="")
        print("\x1B[0m")


# TODO:
# CMD - mouse coordinates include a big buffer scroll up, so instead of 30 we get 1300 for y-val
# Windows Terminal - correct coord

# BUG Windows Terminal
# CMD - generates EventType 0x10 on focus or loss with ENABLE_QUICK_EDIT_MODE
# Terminal - nothing
# without quick edit mode the event for focus loss is not raised
# however this is internal event and should be ignored according to msdn
