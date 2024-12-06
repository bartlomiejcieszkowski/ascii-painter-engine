"""
Python TUI library
"""

__version__ = "0.2.2"
__author__ = "Bartlomiej Cieszkowski <bartlomiej.cieszkowski@gmail.com>"
__license__ = "MIT"

import asyncio
import concurrent.futures
import dataclasses
import logging
import signal
import sys
import threading
from collections import deque
from typing import Union

import retui.input_handling
import retui.terminal
import retui.terminal.base
import retui.widgets
from retui.base import Color, ColorBits, TerminalColor
from retui.mapping import log_widgets

logging.getLogger(__name__).addHandler(logging.NullHandler())
_log = logging.getLogger(__name__)

# TASK LIST:
# TODO: Percent handling inside Pane - guess will need to add start_x, start_y + width height taken from parent
# TODO: Redraw only when covered - blinking over ssh in tmux - temporary: redraw only on size change
# TODO: trim line to screen width on debug prints
# TODO: Relative dimensions, 1 Top 80 percent, 2nd bottom 20 percent - got 1 free line..
# TODO: soft border and docked widget - see docked_dimensions generation

# Notes:
# You can have extra line of console, which won't be fully visible - as w/a just don't use last line
# If new size is greater, then fill with new lines, so we won't be drawing in the middle of screen


def add_window_logger(level: int = logging.DEBUG) -> logging.StreamHandler:
    # TODO move functionality from debug_print here
    pass


class App(retui.widgets.Pane):
    def __init__(self, debug: bool = False, **kwargs):
        if kwargs.get("borderless", None) is None:
            kwargs["borderless"] = True
        if kwargs.get("identifier", None) is None:
            kwargs["identifier"] = "App"
        kwargs["app"] = None
        super().__init__(**kwargs)

        self.terminal = retui.terminal.get_terminal(self)
        self.brush = Brush(self.terminal.vt_supported)
        self.debug_colors = TerminalColor()

        self.running = False
        self.handle_sigint = True

        self.mouse_lmb_state = 0

        self.column_row_widget_cache = {}

        self.demo_thread = None
        self.demo_time_s = None
        self.demo_event = None
        self.emulate_screen_dimensions = None
        self.debug = debug

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

    def debug_print(self, text, end="\n", row_off=-1):
        if self.debug:
            _log.debug(text)
            # TODO
            row = (0 if row_off >= 0 else self.terminal.rows) + row_off
            self.brush.move_cursor(row=row)
            self.brush.print(text, end=end, color=self.debug_colors)

    def clear(self, reuse=True):
        self.dimensions.width, self.dimensions.height = self.terminal.update_size()
        if reuse:
            self.brush.move_cursor(0, 0)
        for line in retui.terminal.TerminalBuffer.get_buffer(
            self.terminal.columns, self.terminal.rows, " ", debug=False
        ):
            self.brush.print(line, end="\n")
        self._update_size = True

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
    def signal_handler(signum, frame):
        App.signal_sigint_ctx.signal_handle(signum, frame)

    def signal_handle(self, signum, frame):
        self.running = False
        _log.debug(f"Signum: {signum}")
        # TODO: read_events is blocking, so this one needs to be somehow inject, otherwise we wait for first new event
        # works accidentally - as releasing ctrl-c cause key event ;)

    def demo_mode(self, time_s):
        self.demo_time_s = time_s

    def emulate_screen(self, height: int, width: int):
        self.emulate_screen_dimensions = (height, width)

    def draw(self, force: bool = False):
        # TODO evaluate need
        if force or self._redraw:
            for widget in self.widgets:
                widget.draw(force=force)
            self._redraw = False
        self.brush.move_cursor(row=self.terminal.rows - 1)

    def update_dimensions(self):
        self._update_size = False
        # TODO For APP always use current - is this correct assumption?
        self.last_dimensions = self.dimensions_copy(last=False)
        self._inner_dimensions = self.calculate_inner_dimensions()
        self.docked_dimensions = dataclasses.replace(self._inner_dimensions)
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
            signal.signal(signal.SIGINT, App.signal_handler)

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
                self.debug_colors = TerminalColor(Color(14, ColorBits.BIT_8), Color(4, ColorBits.BIT_8))
        else:
            self.debug_colors = TerminalColor()
            self.brush.color_mode(enable)
            success = self.terminal.set_color_mode(enable)
        return success


class Brush:
    def __init__(self, use_color=True):
        self.file = sys.stdout
        self.console_color = TerminalColor()
        self.use_color = use_color

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

    def print(self, *args, sep="", end="", color: Union[TerminalColor, None] = None, flush=True):
        if color is None or color.no_color():
            print(*args, sep=sep, end=end, file=self.file, flush=flush)
        else:
            color = self.color(color)
            if color != "":
                print(color, end="", file=self.file)
            print(*args, sep=sep, end="", file=self.file)
            print(self.RESET, sep=sep, end=end, file=self.file, flush=flush)
            self.console_color.reset()

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
