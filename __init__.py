#!/usr/bin/env python3


# Notes:
# You can have extra line of console, which wont be fully visible - as w/a just don't use last line
# If new size is greater, then fill with new lines so we wont be drawing in the middle of screen

# TASK LIST:
# TODO: alignment - current impl always assumes alignment is LEFT_TOP, - handle other cases
# TODO: Percent handling inside Pane - guess will need to add start_x, start_y + width height taken from parent
# TODO: Float layout support
# TODO: Check if whole layout fits console - complain if not
# TODO: Keys and mouse support under Linux
# TODO: Handlers - when clicking given point - pass the event to the widget underneath - required for color selection
# TODO: Redraw only when covered - blinking over ssh in tmux - temporary: redraw only on size change
# TODO: trim line to screen width on debug prints

import shutil
import os
import ctypes
import ctypes.wintypes
import sys

from enum import Flag, Enum, auto, IntEnum
from abc import ABC, abstractmethod
from collections import deque

import signal
from typing import Tuple, Union, List

import ascii_painter_engine.log


def is_windows() -> bool:
    return os.name == 'nt'


if is_windows():
    import msvcrt
else:
    import fcntl
    import termios


class ConsoleBuffer:
    def __init__(self):
        pass

    @staticmethod
    def fill_buffer(x, y, symbol=' ', border=True, debug=True):
        if debug:
            # print numbered border
            buffer = '\n'
            for col in range(0, x):
                buffer += str(col % 10)
            for row in range(1, y + 1):
                buffer += '\n' + str(row % 10) + (symbol * (x - 2)) + str(row % 10)
            return buffer
        if border:
            return ('\n' + (symbol * x)) * y
        return ('\n' + (symbol * x)) * y


class Alignment(Flag):
    Center = 0
    Left = 1
    Right = 2
    Top = 4
    Bottom = 8
    LeftTop = Left | Top
    RightTop = Right | Top
    LeftBottom = Left | Bottom
    RightBottom = Right | Bottom
    Float = 16
    FloatLeftTop = Float | LeftTop
    FloatRightTop = Float | RightTop
    FloatLeftBottom = Float | LeftBottom
    FloatRightBottom = Float | LeftTop
    FloatLeft = Float | Left
    FloatRight = Float | Right
    FloatTop = Float | Top
    FloatBottom = Float | Bottom


class DimensionsFlag(Flag):
    Absolute = 0
    RelativeWidth = 1
    RelativeHeight = 2
    Relative = RelativeWidth | RelativeHeight
    Fill = 4


class Event(Enum):
    MouseClick = auto()


class Rectangle:
    def __init__(self, column: int, row: int, width: int, height: int):
        self.column = column
        self.row = row
        self.width = width
        self.height = height

    def update(self, column: int, row: int, width: int, height: int):
        self.column = column
        self.row = row
        self.width = width
        self.height = height

    def update_tuple(self, dimensions: Union[Tuple[int, int, int, int], List]):
        self.column = dimensions[0]
        self.row = dimensions[1]
        self.width = dimensions[2]
        self.height = dimensions[3]

    def contains_point(self, column: int, row: int):
        return not ((self.row > row) or (self.row + self.height - 1 < row) or (self.column > column) or (
                self.column + self.width - 1 < column))


class InputInterpreter:
    # linux
    # lmb 0, rmb 2, middle 1, wheel up 64 + 0, wheel down 64 + 1

    class State(Enum):
        Default = 0
        Escape = 1
        CSI_Bytes = 2

    # this class should
    # receive data
    # and parse it accordingly
    # if it is ESC then start parsing it as ansi escape code
    # and emit event once we parse whole sequence
    # otherwise pass it to.. input handler?

    # better yet:
    # this class should provide read method, and wrap the input provided

    def __init__(self, readable_input):
        self.input = readable_input
        self.state = self.State.Default
        self.input_raw = []
        self.ansi_escape_sequence = []
        self.payload = deque()
        self.last_button_state = [0, 0, 0]

    # 9 Normal \x1B[ CbCxCy M , value + 32 -> ! is 1 - max 223 (255 - 32)
    # 1006 SGR  \x1B[<Pb;Px;Py[Mm] M - press m - release
    # 1015 URXVT \x1B[Pb;Px;Py M - not recommended, can be mistaken for DL
    # 1016 SGR-Pixel x,y are pixels instead of cells
    # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html

    def parse(self):
        # should append to self.event_list
        length = len(self.ansi_escape_sequence)

        if length < 3:
            # minimal sequence is ESC [ (byte in range 0x40-0x7e)
            self.payload.extend(self.ansi_escape_sequence)
            return

        # we can safely skip first 2 bytes
        # last byte will be character
        if self.ansi_escape_sequence[-1] not in ('m', 'M'):
            self.payload.extend(self.ansi_escape_sequence)
            return

        if self.ansi_escape_sequence[2] == '<':
            # SGR
            idx = 0
            values = [0, 0, 0]
            temp_word = ''
            press = False
            for i in range(3, length + 1):
                ch = self.ansi_escape_sequence[i]
                if idx < 2:
                    if ch == ';':
                        values[idx] = int(temp_word, 10)
                        idx += 1
                        continue
                elif ch in ('m', 'M'):
                    values[idx] = int(temp_word, 10)
                    if ch == 'M':
                        press = True
                    break
                temp_word += ch
            # msft
            # lmb 0x1 rmb 0x2, lmb2 0x4 lmb3 0x8 lmb4 0x10
            # linux
            # lmb 0, rmb 2, middle 1, wheel up 64 + 0, wheel down 64 + 1
            # move 32 + key
            # shift   4
            # meta    8
            # control 16
            self.payload.append(MouseEvent.from_sgr_csi(values[0], values[1], values[2], press))

        # normal - TODO
        self.payload.extend(self.ansi_escape_sequence)
        return

    def read(self, count: int = 1):
        # ESC [ followed by any number in range 0x30-0x3f, then any between 0x20-0x2f, and final byte 0x40-0x7e
        # TODO: this should be limited so if one pastes long, long text this wont create arbitrary size buffer
        ch = self.input.read(count)
        while ch is not None and len(ch) > 0:
            self.input_raw.append(ch)
            ch = self.input.read(count)

        if len(self.input_raw) > 0:
            for i in range(0, len(self.input_raw)):
                ch = self.input_raw[i]
                if self.state != self.State.Default:
                    ord_ch = ord(ch)
                    if 0x20 <= ord_ch <= 0x7f:
                        if self.state == self.State.Escape:
                            if ch == '[':
                                self.ansi_escape_sequence.append(ch)
                                self.state = self.State.CSI_Bytes
                                continue
                        elif self.state == self.State.CSI_Bytes:
                            if 0x30 <= ord_ch <= 0x3f:
                                self.ansi_escape_sequence.append(ch)
                                continue
                            elif 0x40 <= ord_ch <= 0x7e:
                                # implicit IntermediateBytes
                                self.ansi_escape_sequence.append(ch)
                                self.parse()
                                self.state = self.State.Default
                                continue
                    # parse what we had collected so far, since we failed check above
                    self.parse()
                    self.state = self.State.Default
                    # intentionally fall through to regular parse
                # check if escape code
                if ch == '\x1B':
                    self.ansi_escape_sequence.clear()
                    self.ansi_escape_sequence.append(ch)
                    self.state = self.State.Escape
                    continue

                # pass input to handler
                pass
            self.input_raw.clear()

            if len(self.payload) > 0:
                payload = self.payload
                self.payload = deque()
                return payload

        return None


class ConsoleWidget(ABC):
    def __init__(self, console_view, x: int, y: int, width: int, height: int, alignment: Alignment,
                 dimensions: DimensionsFlag = DimensionsFlag.Absolute):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.alignment = alignment
        self.console_view = console_view
        self.dimensions = dimensions
        self.parent = None
        self.handlers = {}
        # register handlers here
        # when handling click - cache what was there to speed up lookup - invalidate on re-draw
        # iterate in reverse order on widgets - the order on widget list determines Z order - higher idx covers lower one
        self.last_dimensions = Rectangle(0, 0, 0, 0)

    def update_dimensions(self):
        # update dimensions is separate, so we separate drawing logic, so if one implement own widget
        # doesn't have to remember to call update_dimensions every time or do it incorrectly
        x = self.x
        y = self.y
        width = self.width_calculated()
        height = self.height_calculated()
        if Alignment.Float in self.alignment:
            # here be dragons
            pass
        else:
            if Alignment.Left in self.alignment:
                #  x
                #   []
                #  0 1 2
                x += self.parent.inner_x()
                pass
            elif Alignment.Right in self.alignment:
                #      x
                #   []
                #  2 1 0
                x = self.parent.inner_x() + self.parent.inner_width() - width - x
                pass

            if Alignment.Top in self.alignment:
                #  y   0
                #   [] 1
                #      2
                y += self.parent.inner_y()
                pass
            elif Alignment.Bottom in self.alignment:
                #      2
                #   [] 0
                #  y   1
                y = self.parent.inner_y() + self.parent.inner_height() - height - y
                pass

        self.last_dimensions.update(x, y, width, height)
        pass

    def get_widget(self, column: int, row: int) -> Union['ConsoleWidget', None]:
        return self if self.contains_point(column, row) else None

    def handle(self, event: Event, coords: Tuple[int, int]):
        # guess we should pass also unknown args
        # raise Exception('handle')
        pass

    @abstractmethod
    def draw(self):
        pass

    def width_calculated(self):
        if DimensionsFlag.RelativeWidth in self.dimensions:
            return (self.width * self.parent.inner_width()) // 100
        elif DimensionsFlag.Fill == self.dimensions:
            return self.parent.inner_width()
        else:
            return self.width

    def height_calculated(self):
        if DimensionsFlag.RelativeHeight in self.dimensions:
            # concern about rows - 1
            return (self.height * self.parent.inner_height()) // 100
        elif DimensionsFlag.Fill == self.dimensions:
            return self.parent.inner_height()
        else:
            return self.height

    def contains_point(self, column: int, row: int):
        return self.last_dimensions.contains_point(column, row)


class ConsoleWidgets:
    class BorderWidget(ConsoleWidget):
        def __init__(self, console_view, x: int, y: int, width: int, height: int, alignment: Alignment,
                     dimensions: DimensionsFlag = DimensionsFlag.Absolute, borderless: bool = False):
            super().__init__(console_view=console_view, x=x, y=y, width=width, height=height, alignment=alignment,
                             dimensions=dimensions)
            self.borderless = borderless
            self.title = ''
            # border string
            # 155552
            # 600007
            # 600007
            # 388884
            # where the string is in form
            # '012345678'
            self.border = [
                BorderPoint(' '),
                BorderPoint('+'),
                BorderPoint('+'),
                BorderPoint('+'),
                BorderPoint('+'),
                BorderPoint('-'),
                BorderPoint('|'),
                BorderPoint('|'),
                BorderPoint('-'),
            ]
            # self.border = [
            #     BorderPoint(' '),
            #     BorderPoint(' '),
            #     BorderPoint(' '),
            #     BorderPoint('|'),
            #     BorderPoint('|'),
            #     BorderPoint('_'),
            #     BorderPoint('|'),
            #     BorderPoint('|'),
            #     BorderPoint('_'),
            # ]

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
                raise Exception(f'border_str must have at least len of 9 - got {len(border_str)}')
            for i in range(0, 9):
                self.border[i] = BorderPoint(border_str[i])

        def border_set_color(self, color):
            for i in range(1, 9):
                self.border[i].color = color

        def border_inside_set_color(self, color):
            self.border[0].color = color

        def border_get_top(self, width_middle, title):
            return self.console_view.brush.FgBgColor(self.border[1].color) + \
                   self.border[1].c + \
                   self.console_view.brush.FgBgColor(self.border[5].color) + \
                   ((title[:width_middle - 2] + '..') if len(title) > width_middle else title) + \
                   (self.border[5].c * (width_middle - len(self.title))) + \
                   self.console_view.brush.FgBgColor(self.border[2].color) + \
                   self.border[2].c + \
                   self.console_view.brush.ResetColor()

        def border_get_bottom(self, width_middle):
            return self.console_view.brush.FgBgColor(self.border[3].color) + \
                   self.border[3].c + \
                   self.console_view.brush.FgBgColor(self.border[8].color) + \
                   (self.border[8].c * width_middle) + \
                   self.console_view.brush.FgBgColor(self.border[4].color) + \
                   self.border[4].c + \
                   self.console_view.brush.ResetColor()

        def draw(self):
            self.draw_bordered(title=self.title)

        def draw_bordered(self, inside_text: str = '', title: str = ''):
            offset_rows = self.last_dimensions.row
            offset_cols = self.last_dimensions.column
            width = self.last_dimensions.width
            height = self.last_dimensions.height
            width_middle = width
            if self.borderless is False:
                width_middle -= 2
            self.console_view.brush.MoveCursor(row=offset_rows)
            offset_str = self.console_view.brush.MoveRight(offset_cols)
            if self.borderless is False:
                self.console_view.brush.print(offset_str + self.border_get_top(width_middle, title), end='')
            text = inside_text
            start = 0 if self.borderless else 1
            end = height if self.borderless else (height - 1)
            for h in range(start, end):
                self.console_view.brush.MoveCursor(row=offset_rows + h)
                # split string ?
                print_text = text
                if len(text) > width_middle and len(text) != 0:
                    # split
                    print_text = text[0:width_middle]
                    text = text[width_middle:]
                else:
                    text = ''
                leftover = width_middle - len(print_text)
                line = offset_str

                if self.borderless is False:
                    line += self.console_view.brush.FgBgColor(self.border[6].color) + \
                            self.border[6].c

                line += self.console_view.brush.FgBgColor(self.border[0].color) + print_text + \
                        (self.border[0].c * leftover)

                if self.borderless is False:
                    line += self.console_view.brush.FgBgColor(self.border[7].color) + \
                            self.border[7].c

                line += self.console_view.brush.ResetColor()
                self.console_view.brush.print(line, end='')

            if self.borderless is False:
                self.console_view.brush.MoveCursor(row=offset_rows + height - 1)
                self.console_view.brush.print(offset_str + self.border_get_bottom(width_middle), end='\n')
            pass

    class TextBox(BorderWidget):
        def __init__(self, console_view, x: int, y: int, width: int, height: int, alignment: Alignment,
                     dimensions: DimensionsFlag = DimensionsFlag.Absolute, borderless: bool = False):
            super().__init__(console_view=console_view, x=x, y=y, width=width, height=height, alignment=alignment,
                             dimensions=dimensions, borderless=borderless)
            self.text = ''

        def draw(self):
            return self.draw_bordered(inside_text=self.text, title=self.title)

    class Pane(BorderWidget):
        def __init__(self, console_view, x: int, y: int, width: int, height: int,
                     alignment: Alignment, dimensions: DimensionsFlag = DimensionsFlag.Absolute,
                     borderless: bool = False):
            super().__init__(console_view=console_view, x=x, y=y, width=width, height=height, alignment=alignment,
                             dimensions=dimensions, borderless=borderless)
            self.widgets = []

        def draw(self):
            self.draw_bordered(inside_text='', title=self.title)
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

        def get_widget(self, column: int, row: int) -> Union['ConsoleWidget', None]:
            for idx in range(len(self.widgets) - 1, -1, -1):
                widget = self.widgets[idx].get_widget(column, row)
                if widget:
                    return widget

            return super().get_widget(column, row)


class Console:
    def __init__(self, console_view, debug=True):
        # TODO: this would print without vt enabled yet update state if vt enabled in brush?
        self.console_view = console_view
        self.columns, self.rows = self.get_size()
        self.vt_supported = False
        self.debug = debug
        pass

    def update_size(self):
        self.columns, self.rows = self.get_size()
        self.rows -= 2
        return self.columns, self.rows

    @staticmethod
    def get_size():
        columns, rows = shutil.get_terminal_size(fallback=(0, 0))
        # self.debug_print(f'{columns}x{rows}')
        return columns, rows

    def set_color_mode(self, enable: bool) -> bool:
        self.vt_supported = enable
        return enable

    @abstractmethod
    def interactive_mode(self):
        pass

    @abstractmethod
    def read_events(self, callback, callback_ctx) -> bool:
        pass


class LinuxConsole(Console):
    # TODO
    def __init__(self, console_view):
        super().__init__(console_view)
        self.is_interactive_mode = False
        self.window_changed = False
        self.prev_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        new_fl = self.prev_fl | os.O_NONBLOCK
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, new_fl)
        self.console_view.log(f'stdin fl: 0x{self.prev_fl:X} -> 0x{new_fl:X}')
        self.prev_tc = termios.tcgetattr(sys.stdin)
        new_tc = termios.tcgetattr(sys.stdin)
        # manipulating lflag
        new_tc[3] = new_tc[3] & ~termios.ECHO  # disable input echo
        new_tc[3] = new_tc[3] & ~termios.ICANON  # disable canonical mode - input available immediately
        # cc
        new_tc[6][termios.VMIN] = 0  # cc - minimum bytes
        new_tc[6][termios.VTIME] = 0  # cc - minimum time
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_tc)  # TCSADRAIN?
        self.console_view.log(f'stdin lflags: 0x{self.prev_tc[3]:X} -> 0x{new_tc[3]:X}')
        self.console_view.log(f'stdin cc VMIN: 0x{self.prev_tc[6][termios.VMIN]} -> 0x{new_tc[6][termios.VMIN]}')
        self.console_view.log(f'stdin cc VTIME: 0x{self.prev_tc[6][termios.VTIME]} -> 0x{new_tc[6][termios.VTIME]}')

        self.input_interpreter = InputInterpreter(sys.stdin)

    def __del__(self):
        # restore stdin
        if self.is_interactive_mode:
            print('\x1B[?10001')

        termios.tcsetattr(sys.stdin, termios.TCSANOW, self.prev_tc)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self.prev_fl)
        print('')
        print('Restore console done')
        if self.is_intercative_mode:
            print('\x1B[?1006l\x1B[?1015l\x1B[?1003l')

    window_change_event_ctx = None

    @staticmethod
    def window_change_handler(signum, frame):
        LinuxConsole.window_change_event_ctx.window_change_event()

    def window_change_event(self):
        # inject special input on stdin?
        self.window_changed = True

    def interactive_mode(self):
        self.is_interactive_mode = True
        LinuxConsole.window_change_event_ctx = self
        signal.signal(signal.SIGWINCH, LinuxConsole.window_change_handler)
        # ctrl-z not allowed
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        # enable mouse - xterm, sgr1006
        print('\x1B[?1003h\x1B[?1006h')

    def read_events(self, callback, callback_ctx) -> bool:
        events_list = []

        if self.window_changed:
            self.window_changed = False
            events_list.append(SizeChangeEvent())
        else:
            ret = self.input_interpreter.read()
            if ret:
                # passing around deque..
                events_list.append(ret)

        if len(events_list):
            callback(callback_ctx, events_list)
        return True


def no_print(fmt, *args):
    pass


class ConsoleView:
    def __init__(self, log=no_print):
        self.log = log

        if is_windows():
            self.console = WindowsConsole(self)
        else:
            self.console = LinuxConsole(self)
        self.widgets = []
        self.brush = Brush(self.console.vt_supported)
        self.debug_colors = ConsoleColor(None, None)
        self.run = True
        self.requires_draw = False
        self.width = 0
        self.height = 0

        self.mouse_lmb_state = 0

        self.column_row_widget_cache = {}

    def inner_x(self):
        return 0

    def inner_y(self):
        return 0

    def inner_width(self):
        return self.width

    def inner_height(self):
        return self.height

    def debug_print(self, text, end='\n'):
        if self.log is not no_print:
            self.brush.print(text, color=self.debug_colors, end=end)

    def clear(self, reuse=True):
        self.width, self.height = self.console.update_size()
        if reuse:
            self.brush.MoveCursor(0, 0)
        print(ConsoleBuffer.fill_buffer(self.console.columns, self.console.rows, ' ', border=False, debug=False),
              end='\n')
        self.requires_draw = True

    def get_widget(self, column: int, row: int) -> Union[ConsoleWidget, None]:
        for idx in range(len(self.widgets) - 1, -1, -1):
            widget = self.widgets[idx].get_widget(column, row)
            if widget:
                return widget
        return None

    def handle_click(self, column: int, row: int):
        # naive cache - based on clicked point
        # pro - we can create heat map
        # cons - it would be better with rectangle
        widget = self.column_row_widget_cache.get((column, row), 1)
        if type(widget) is int:
            widget = self.get_widget(column, row)
            self.column_row_widget_cache[(column, row)] = widget
        if widget:
            widget.handle(Event.MouseClick, (row, column))

        widget = widget.title if widget else widget
        return widget

    @staticmethod
    def handle_events_callback(ctx, events_list):
        ctx.handle_events(events_list)

    def handle_events(self, events_list):
        off = -2
        # with -1 - 2 lines nearest end of screen overwrite each other
        for event in events_list:
            if isinstance(event, deque):
                self.handle_events(event)
            elif isinstance(event, list):
                self.handle_events(event)
            elif isinstance(event, MouseEvent):
                # we could use mask here, but then we will handle holding right button and
                # pressing/releasing left button and other combinations and frankly i don't want to
                # if (event.button_state & 0x1) == 0x1 and event.event_flags == 0:
                release = False
                widget = None
                if event.button == event.button.LMB and event.pressed is False:
                    widget = self.handle_click(event.coordinates[0], event.coordinates[1])

                self.brush.MoveCursor(row=(self.console.rows + off) - 1)
                if widget:
                    self.log(f'x: {event.coordinates[0]} y:{event.coordinates[1]} button:{event.button} press:{event.pressed} widget:{widget}')
            elif isinstance(event, SizeChangeEvent):
                self.clear()
                self.brush.MoveCursor(row=(self.console.rows + off) - 0)
                self.debug_print(f'size: {self.console.columns:3}x{self.console.rows:3}')
            elif isinstance(event, KeyEvent):
                self.brush.MoveCursor(row=(self.console.rows + off) - 2)
                self.debug_print(
                    f'vk_code: {hex(event.vk_code)} pressed? {event.key_down}'
                )
            else:
                pass

    signal_sigint_ctx = None

    @staticmethod
    def signal_sigint_handler(signum, frame):
        ConsoleView.signal_sigint_ctx.signal_sigint()

    def signal_sigint(self):
        self.run = False
        # TODO: read_events is blocking, sos this one needs to be somehow inject, otherwise we wait for first new event
        # works accidentally - as releasing ctrl-c cause key event ;)

    def loop(self, handle_sigint) -> int:
        if handle_sigint:
            ConsoleView.signal_sigint_ctx = self
            signal.signal(signal.SIGINT, ConsoleView.signal_sigint_handler)

        self.run = True

        # create blank canvas
        self.clear(reuse=False)

        self.console.interactive_mode()

        self.brush.HideCursor()
        self.handle_events([SizeChangeEvent()])
        i = 0
        while self.run:
            if self.requires_draw:
                self.column_row_widget_cache.clear()
                for widget in self.widgets:
                    widget.update_dimensions()
                for widget in self.widgets:
                    widget.draw()
                self.brush.MoveCursor(row=self.console.rows - 1)
                self.requires_draw = False
            # this is blocking
            if not self.console.read_events(self.handle_events_callback, self):
                break
            i += 1
        # Move to the end, so we wont end up writing in middle of screen
        self.brush.MoveCursor(self.console.rows - 1)
        self.brush.ShowCursor()
        return 0

    def color_mode(self) -> bool:
        success = self.console.set_color_mode(True)
        if success:
            self.brush.color_mode()
            self.debug_colors = ConsoleColor(Color(14, ColorBits.Bit8), Color(4, ColorBits.Bit8))
        return success

    def nocolor_mode(self) -> bool:
        self.debug_colors = ConsoleColor(None, None)
        self.brush.nocolor_mode()
        return self.console.set_color_mode(False)

    def add_widget(self, widget: ConsoleWidget) -> None:
        widget.parent = self
        self.widgets.append(widget)

    def add_widget_after(self, widget: ConsoleWidget, widget_on_list: ConsoleWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError as e:
            return False

        widget.parent = self
        self.widgets.insert(idx + 1, widget)
        return True

    def add_widget_before(self, widget: ConsoleWidget, widget_on_list: ConsoleWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError as e:
            return False

        widget.parent = self
        self.widgets.insert(idx, widget)
        return True


class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.wintypes.SHORT),
                ("Y", ctypes.wintypes.SHORT)]


class KEY_EVENT_RECORD_Char(ctypes.Union):
    _fields_ = [("UnicodeChar", ctypes.wintypes.WCHAR),
                ("AsciiChar", ctypes.wintypes.CHAR)]


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("bKeyDown", ctypes.wintypes.BOOL),
                ("wRepeatCount", ctypes.wintypes.WORD),
                ("wVirtualKeyCode", ctypes.wintypes.WORD),
                ("wVirtualScanCode", ctypes.wintypes.WORD),
                ("uChar", KEY_EVENT_RECORD_Char),
                ("dwControlKeyState", ctypes.wintypes.DWORD)]


class MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("dwMousePosition", COORD),
                ("dwButtonState", ctypes.wintypes.DWORD),
                ("dwControlKeyState", ctypes.wintypes.DWORD),
                ("dwEventFlags", ctypes.wintypes.DWORD)]


class INPUT_RECORD_Event(ctypes.Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD),
                ("MouseEvent", MOUSE_EVENT_RECORD),
                ("WindowBufferSizeEvent", COORD),
                ("MenuEvent", ctypes.c_uint),
                ("FocusEvent", ctypes.c_uint),
                ]


class INPUT_RECORD(ctypes.Structure):
    _fields_ = [("EventType", ctypes.wintypes.WORD),
                ("Event", INPUT_RECORD_Event)]


class ConsoleEvent(ABC):
    def __init__(self):
        pass


class SizeChangeEvent(ConsoleEvent):
    def __init__(self):
        super().__init__()


class MouseEvent(ConsoleEvent):
    last_mask = 0x0

    class Buttons(IntEnum):
        LMB = 0,
        RMB = 2,
        MIDDLE = 1,
        WHEEL_UP = 64,
        WHEEL_DOWN = 65

    class ControlKeys(Flag):
        LEFT_CTRL = 0x8

    def __init__(self, x, y, button: Buttons, pressed: bool, control_key_state):
        super().__init__()
        self.coordinates = (x, y)
        self.button = button
        self.pressed = pressed
        # based on https://docs.microsoft.com/en-us/windows/console/mouse-event-record-str
        # but simplified - right ctrl => left ctrl
        self.control_key_state = control_key_state

    @classmethod
    def from_windows_event(cls, mouse_event_record: MOUSE_EVENT_RECORD):
        # on windows position is 0-based, top-left corner, row 0 is inaccessible, translate Y as Y-1
        if mouse_event_record.dwMousePosition.Y == 0:
            return None

        # zero indicates mouse button is pressed or released
        if mouse_event_record.dwEventFlags != 0:
            if mouse_event_record.dwEventFlags == 0x1:
                # mouse move - TODO: hover implementation
                pass
            if mouse_event_record.dwEventFlags == 0x4:
                # mouse wheel move, high word of dwButtonState is dir, positive up
                return cls(mouse_event_record.dwMousePosition.X,
                           mouse_event_record.dwMousePosition.Y - 1,
                           MouseEvent.Buttons(MouseEvent.Buttons.WHEEL_UP + ((mouse_event_record.dwButtonState >> 31) & 0x1)),
                           True,
                           None
                           )
                # TODO: high word
                pass
            elif mouse_event_record.dwEventFlags == 0x8:
                # horizontal mouse wheel - NOT SUPPORTED
                pass
            elif mouse_event_record.dwEventFlags == 0x2:
                # double click - TODO: do we need this?
                pass
            return None

        ret_list = []

        # on windows we get mask of pressed buttons
        # we can either pass mask around and worry about translating it outside
        # we will have two different handlings on windows and linux
        # so we just translate it into serialized clicks
        changed_mask = mouse_event_record.dwButtonState ^ MouseEvent.last_mask

        if changed_mask == 0:
            return None

        MouseEvent.last_mask = mouse_event_record.dwButtonState

        for idx in [0, 1, 2]:
            changed = changed_mask & (0x1 << idx)
            if changed:
                press = (mouse_event_record.dwButtonState & (0x1 << idx) != 0)

                event = cls(mouse_event_record.dwMousePosition.X,
                            mouse_event_record.dwMousePosition.Y - 1,
                            MouseEvent.Buttons(idx),
                            press,
                            None)
                ret_list.append(event)

        if len(ret_list) == 0:
            return None

        return ret_list

    @classmethod
    def from_sgr_csi(cls, button_hex: int, x: int, y: int, press: bool):
        move_event = button_hex & 32
        if move_event:
            return None

        wheel_event = button_hex & 64
        ctrl_button = 0x8 if button_hex & 16 else 0x0

        # remove ctrl button
        button_hex = button_hex & (0xFFFFFFFF - 0x10)

        button = MouseEvent.Buttons(button_hex)
        return cls(x, y, button, press, ctrl_button)


class KeyEvent(ConsoleEvent):
    def __init__(self, key_down: bool, repeat_count: int, vk_code: int, vs_code: int, char, control_key_state):
        super().__init__()
        self.key_down = key_down
        self.repeat_count = repeat_count
        self.vk_code = vk_code
        self.vs_code = vs_code
        self.char = char
        self.control_key_state = control_key_state


class WindowsConsole(Console):
    def __init__(self, console_view):
        super().__init__(console_view)
        self.kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        set_console_mode_proto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD
        )
        set_console_mode_params = (1, "hConsoleHandle", 0), (1, "dwMode", 0)
        self.setConsoleMode = set_console_mode_proto(('SetConsoleMode', self.kernel32), set_console_mode_params)

        get_console_mode_proto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPDWORD
        )
        get_console_mode_params = (1, "hConsoleHandle", 0), (1, "lpMode", 0)
        self.getConsoleMode = get_console_mode_proto(('GetConsoleMode', self.kernel32), get_console_mode_params)
        self.consoleHandleOut = msvcrt.get_osfhandle(sys.stdout.fileno())
        self.consoleHandleIn = msvcrt.get_osfhandle(sys.stdin.fileno())

        read_console_input_proto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPVOID,  # PINPUT_RECORD
            ctypes.wintypes.DWORD,
            ctypes.wintypes.LPDWORD
        )
        read_console_input_params = (1, "hConsoleInput", 0), (1, "lpBuffer", 0), (1, "nLength", 0), (
            1, "lpNumberOfEventsRead", 0)
        self.readConsoleInput = read_console_input_proto(('ReadConsoleInputW', self.kernel32),
                                                         read_console_input_params)

    KEY_EVENT = 0x1
    MOUSE_EVENT = 0x2
    WINDOW_BUFFER_SIZE_EVENT = 0x4

    def interactive_mode(self):
        self.SetWindowChangeSizeEvents(True)
        self.SetMouseInput(True)

    def read_events(self, callback, callback_ctx) -> bool:
        events_list = []
        # TODO: N events
        record = INPUT_RECORD()
        events = ctypes.wintypes.DWORD(0)
        ret_val = self.readConsoleInput(self.consoleHandleIn, ctypes.byref(record), 1, ctypes.byref(events))
        # print(f'\rret:{ret_val} EventType:{hex(record.EventType)}', end='')

        if record.EventType == self.WINDOW_BUFFER_SIZE_EVENT:
            events_list.append(SizeChangeEvent())
        elif record.EventType == self.MOUSE_EVENT:
            event = MouseEvent.from_windows_event(record.Event.MouseEvent)
            if event:
                events_list.append(event)
        elif record.EventType == self.KEY_EVENT:
            events_list.append(KeyEvent(key_down=record.Event.KeyEvent.bKeyDown,
                                        repeat_count=record.Event.KeyEvent.wRepeatCount,
                                        vk_code=record.Event.KeyEvent.wVirtualKeyCode,
                                        vs_code=record.Event.KeyEvent.wVirtualScanCode,
                                        char=record.Event.KeyEvent.uChar.AsciiChar,
                                        control_key_state=record.Event.KeyEvent.dwControlKeyState))
        else:
            pass

        if len(events_list):
            callback(callback_ctx, events_list)
        return True

    def GetConsoleMode(self, handle) -> int:
        dwMode = ctypes.wintypes.DWORD(0)
        # lpMode = ctypes.wintypes.LPDWORD(dwMode)
        # don't create pointer if not going to use it in python, use byref
        self.getConsoleMode(handle, ctypes.byref(dwMode))

        # print(f' dwMode: {hex(dwMode.value)}')
        return dwMode.value

    def SetConsoleMode(self, handle, mode: int):
        dwMode = ctypes.wintypes.DWORD(mode)
        self.setConsoleMode(handle, dwMode)
        return

    def SetMode(self, handle, mask: int, enable: bool) -> bool:
        console_mode = self.GetConsoleMode(handle)
        other_bits = mask ^ 0xFFFFFFFF
        expected_value = mask if enable else 0
        if (console_mode & mask) == expected_value:
            return True

        console_mode = (console_mode & other_bits) | expected_value
        self.SetConsoleMode(handle, console_mode)
        console_mode = self.GetConsoleMode(handle)
        return (console_mode & mask) == expected_value

    def SetVirtualTerminalProcessing(self, enable: bool) -> bool:
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4
        return self.SetMode(self.consoleHandleOut, ENABLE_VIRTUAL_TERMINAL_PROCESSING, enable)

    def set_color_mode(self, enable: bool) -> bool:
        success = self.SetVirtualTerminalProcessing(enable)
        return super().set_color_mode(enable & success)

    def SetWindowChangeSizeEvents(self, enable: bool) -> bool:
        ENABLE_WINDOW_INPUT = 0x8
        return self.SetMode(self.consoleHandleIn, ENABLE_WINDOW_INPUT, enable)

    def SetQuickEditMode(self, enable: bool) -> bool:
        ENABLE_QUICK_EDIT_MODE = 0x40
        return self.SetMode(self.consoleHandleIn, ENABLE_QUICK_EDIT_MODE, enable)

    def SetMouseInput(self, enable: bool) -> bool:
        # Quick Edit Mode blocks mouse events
        self.SetQuickEditMode(False)
        ENABLE_MOUSE_INPUT = 0x10
        return self.SetMode(self.consoleHandleIn, ENABLE_MOUSE_INPUT, enable)


class ColorBits(IntEnum):
    Bit8 = 5
    Bit24 = 2


class Color:
    def __init__(self, color: int, bits: ColorBits):
        self.color = color
        self.bits = bits


class ConsoleColor:
    def __init__(self, fgcolor: Union[Color, None] = None, bgcolor: Union[Color, None] = None):
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor

    def no_color(self):
        return self.fgcolor is None and self.bgcolor is None


class BorderPoint:
    def __init__(self, c: str = ' ', color: ConsoleColor = ConsoleColor()):
        self.c = c
        self.color = color


class Brush:
    def __init__(self, use_color=True):
        self.fgcolor = None
        self.bgcolor = None
        self.use_color = use_color

    RESET = '\x1B[0m'

    def color_mode(self):
        self.use_color = True

    def nocolor_mode(self):
        self.use_color = False

    def FgColor(self, color, check_last=False, bits: ColorBits = ColorBits.Bit24):
        if check_last:
            if self.fgcolor == color:
                return ''
        self.fgcolor = color
        if self.fgcolor is None:
            return ''
        return f'\x1B[38;{int(self.fgcolor.bits)};{self.fgcolor.color}m'

    def BgColor(self, color: Color, check_last=False):
        if check_last:
            if self.bgcolor == color:
                return ''
        self.bgcolor = color
        if self.bgcolor is None:
            return ''
        return f'\x1B[48;{int(self.bgcolor.bits)};{self.bgcolor.color}m'

    def FgBgColor(self, console_color: ConsoleColor, check_last=False):
        ret_val = ''
        if (console_color.fgcolor is None and self.fgcolor != console_color.fgcolor) or (
                console_color.bgcolor is None and self.bgcolor != console_color.bgcolor):
            ret_val = self.ResetColor()
        ret_val += self.FgColor(console_color.fgcolor, check_last)
        ret_val += self.BgColor(console_color.fgcolor, check_last)
        return ret_val

    def print(self, *args, sep=' ', end='', file=None, color: Union[ConsoleColor, None] = None):
        if color is None or color.no_color():
            print(*args, sep=sep, end=end, file=file)
        else:
            color = self.BgColor(color.bgcolor) + self.FgColor(color.fgcolor)
            print(color + " ".join(map(str, args)) + self.RESET, sep=sep, end=end, file=file)

    def SetFgColor(self, color):
        print(self.FgColor(color), end='')

    def SetBgColor(self, color):
        print(self.BgColor(color), end='')

    def ResetColor(self):
        self.bgcolor = None
        self.fgcolor = None
        return self.RESET

    @staticmethod
    def Reset():
        print(Brush.RESET, end='')

    @staticmethod
    def MoveUp(cells: int = 1):
        print(f'\x1B[{cells}A')

    @staticmethod
    def MoveDown(cells: int = 1):
        print(f'\x1B[{cells}B')

    @staticmethod
    def MoveRight(cells: int = 1) -> str:
        if cells != 0:
            return f'\x1B[{cells}C'
        return ''

    @staticmethod
    def MoveLeft(cells: int = 1) -> str:
        if cells != 0:
            return f'\x1B[{cells}D'
        return ''

    @staticmethod
    def MoveLineDown(lines: int = 1):
        print(f'\x1B[{lines}E')  # not ANSI.SYS

    @staticmethod
    def MoveLineUp(lines: int = 1):
        print(f'\x1B[{lines}F')  # not ANSI.SYS

    @staticmethod
    def MoveColumnAbsolute(column: int = 1):
        print(f'\x1B[{column}G')  # not ANSI.SYS

    @staticmethod
    def MoveCursor(row: int = 0, column: int = 0):
        print(f'\x1B[{row + 1};{column + 1}H')

    @staticmethod
    def HorizontalVerticalPosition(row: int = 1, column: int = 1):
        print(f'\x1B[{row};{column}f')

    @staticmethod
    def HideCursor():
        print('\x1b[?25l')
        # alternative on windows without vt:
        # https://docs.microsoft.com/en-us/windows/console/setconsolecursorinfo?redirectedfrom=MSDN

    @staticmethod
    def ShowCursor():
        print('\x1b[?25h')


class Test:
    @staticmethod
    def ColorLine(start, end, text='  ', use_color=False, width=2):
        for color in range(start, end):
            print(f'\x1B[48;5;{color}m{("{:" + str(width) + "}").format(color) if use_color else text}', end='')
        print('\x1B[0m')

    @staticmethod
    def ColorLine24bit(start, end, step=0):
        for color in range(start, end, step):
            print(f'\x1B[48;2;{color};{color};{color}mXD', end='')
        print('\x1B[0m')

# TODO:
# CMD - mouse coordinates include a big buffer scroll up, so instead of 30 we get 1300 for y-val
# Windows Terminal - correct coord

# BUG Windows Terminal
# CMD - generates EventType 0x10 on focus or loss with ENABLE_QUICK_EDIT_MODE
# Terminal - nothing
# without quick edit mode the event for focus loss is not raised
# however this is internal event and should be ignored according to msdn
