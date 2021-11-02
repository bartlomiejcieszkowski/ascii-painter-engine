#!/usr/bin/env python3


# Notes:
# You can have extra line of console, which wont be fully visible - as w/a just don't use last line
# If new size is greater, then fill with new lines so we wont be drawing in the middle of screen

# TASK LIST:
# TODO: Redraw only when covered - blinking over ssh in tmux - temporary: redraw only on size change
# TODO: Percent - current impl allows only specifying percent for both dimensions
# TODO: alignment - current impl always assumes alignment is LEFT_TOP, - handle other cases
# TODO: Percent handling inside Pane - guess will need to add start_x, start_y + width height taken from parent
# TODO: Float layout support
# TODO: Check if whole layout fits console - complain if not
# TODO: Keys and mouse support under Linux
# TODO: Handlers - when clicking given point - pass the event to the widget underneath - required for color selection


import shutil
import os
import ctypes
import ctypes.wintypes
import sys

from enum import Enum, auto
from abc import ABC, abstractmethod

import signal


def is_windows() -> bool:
    return os.name == 'nt'


if is_windows():
    import msvcrt


class ConsoleBuffer:
    def __init__(self):
        pass

    @staticmethod
    def fill_buffer(x, y, symbol=' ', border=True):
        if border:
            return ('\n' + '.' + (symbol * (x - 2)) + '.') * y
        return ('\n' + (symbol * x)) * y


class ConsoleWidgetAlignment(Enum):
    LEFT_TOP = auto()
    RIGHT_TOP = auto()
    LEFT_BOTTOM = auto()
    RIGHT_BOTTOM = auto()


class ConsoleWidget(ABC):
    def __init__(self, console_view, x: int, y: int, width: int, height: int, alignment: ConsoleWidgetAlignment,
                 percent: bool = False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.alignment = alignment
        self.console_view = console_view
        self.percent = percent

    @abstractmethod
    def draw(self):
        pass

    def width_calculated(self):
        return ((self.width * (self.console_view.console.size[0])) // 100) if self.percent else self.width

    def height_calculated(self):
        return ((self.height * (self.console_view.console.size[1] - 2)) // 100) if self.percent else self.height


class BorderPoint:
    def __init__(self, c: str = ' ', color=(None, None)):
        self.c = c
        self.color = color


class ConsoleWidgets:
    class BorderWidget(ConsoleWidget):
        def __init__(self, console_view, x: int, y: int, width: int, height: int, alignment: ConsoleWidgetAlignment,
                     percent: bool = False):
            super().__init__(console_view=console_view, x=x, y=y, width=width, height=height, alignment=alignment,
                             percent=percent)
            self.borderless = False
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

        def draw_bordered(self, inside_text: str = '', title: str = ''):
            width = self.width_calculated()
            height = self.height_calculated()
            width_middle = width
            if self.borderless is False:
                width_middle -= 2
            self.console_view.brush.MoveCursor(row=self.y)
            offset_str = self.console_view.brush.MoveRight(self.x)
            if self.borderless is False:
                self.console_view.brush.print(offset_str + self.border_get_top(width_middle, title), end='')
            text = inside_text
            start = 0 if self.borderless else 1
            end = height if self.borderless else (height - 1)
            for h in range(start, end):
                self.console_view.brush.MoveCursor(row=self.y + h)
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
                self.console_view.brush.MoveCursor(row=self.y + height - 1)
                self.console_view.brush.print(offset_str + self.border_get_bottom(width_middle), end='\n')
            pass

    class TextBox(BorderWidget):
        def __init__(self, console_view, x: int, y: int, width: int, height: int, alignment: ConsoleWidgetAlignment,
                     percent: bool = False):
            super().__init__(console_view=console_view, x=x, y=y, width=width, height=height, alignment=alignment,
                             percent=percent)
            self.text = ''

        def draw(self):
            return self.draw_bordered(inside_text=self.text, title=self.title)

    class Pane(BorderWidget):
        def __init__(self, console_view, x: int, y: int, width: int, height: int,
                     alignment: ConsoleWidgetAlignment, percent: bool = False):
            super().__init__(console_view=console_view, x=x, y=y, width=width, height=height, alignment=alignment,
                             percent=percent)
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
            widget.x += self.x + 1
            widget.y += self.y + 1
            self.widgets.append(widget)


class Console:
    def __init__(self, debug=True):
        # TODO: this would print without vt enabled yet update state if vt enabled in brush?
        self.size = self.get_size()
        self.vt_supported = False
        self.debug = debug
        pass

    def update_size(self):
        self.size = self.get_size()

    @staticmethod
    def get_size():
        terminal_size = shutil.get_terminal_size(fallback=(0, 0))
        # self.debug_print(f'{terminal_size[0]}x{terminal_size[1]}')
        return terminal_size

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
    def __init__(self):
        super().__init__()
        self.window_changed = False

    window_change_event_ctx = None

    @staticmethod
    def window_change_handler(signum, frame):
        LinuxConsole.window_change_event_ctx.window_change_event()

    def window_change_event(self):
        # inject special input on stdin?
        self.window_changed = True

    def interactive_mode(self):
        LinuxConsole.window_change_event_ctx = self
        signal.signal(signal.SIGWINCH, LinuxConsole.window_change_handler)

    def read_events(self, callback, callback_ctx) -> bool:
        events_list = []

        if self.window_changed:
            self.window_changed = False
            events_list.append(SizeChangeEvent())
        else:
            pass

        callback(callback_ctx, events_list)
        return True


class ConsoleView:
    def __init__(self, debug=False):
        if is_windows():
            self.console = WindowsConsole()
        else:
            self.console = LinuxConsole()
        self.widgets = []
        self.brush = Brush(self.console.vt_supported)
        self.debug = debug
        self.debug_colors = (None, None)  # 14, 4
        self.run = True
        self.requires_draw = False

    def debug_print(self, text, end='\n'):
        if self.debug:
            self.brush.print(text, fgcolor=self.debug_colors[0], bgcolor=self.debug_colors[1], end=end)

    def clear(self, reuse=True):
        self.console.update_size()
        if reuse:
            self.brush.MoveCursor(1, 1)
        print(ConsoleBuffer.fill_buffer(self.console.size[0], self.console.size[1], ' '), end='')
        self.requires_draw = True

    @staticmethod
    def handle_events_callback(ctx, events_list):
        ctx.handle_events(events_list)

    def handle_events(self, events_list):
        off = -2
        # with -1 - we lines 2 near end of screen overwrite each other
        for event in events_list:
            if isinstance(event, MouseEvent):
                self.brush.MoveCursor(row=(self.console.size[1] + off) - 1)
                self.debug_print(
                    f'mouse coord: x:{event.coordinates[0]:3} y:{event.coordinates[1]:3}')
            elif isinstance(event, SizeChangeEvent):
                self.clear()
                self.brush.MoveCursor(row=(self.console.size[1] + off) - 0)
                self.debug_print(f'size: {self.console.size[0]:3}x{self.console.size[1]:3}')
            elif isinstance(event, KeyEvent):
                self.brush.MoveCursor(row=(self.console.size[1] + off) - 2)
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
        self.console.update_size()

        # create blank canvas
        self.clear(reuse=False)

        self.console.interactive_mode()

        self.brush.HideCursor()
        self.handle_events([SizeChangeEvent()])
        i = 0
        while self.run:
            if self.requires_draw:
                for widget in self.widgets:
                    widget.draw()
                self.brush.MoveCursor(row=self.console.size[1] - 1)
                self.requires_draw = False
            # this is blocking
            if not self.console.read_events(self.handle_events_callback, self):
                break
            i += 1
        # Move to the end, so we wont end up writing in middle of screen
        self.brush.MoveCursor(self.console.size[1] - 1)
        return 0

    def color_mode(self) -> bool:
        success = self.console.set_color_mode(True)
        if success:
            self.brush.color_mode()
            self.debug_colors = (14, 4)
        return success

    def nocolor_mode(self) -> bool:
        self.debug_colors = (None, None)
        self.brush.nocolor_mode()
        return self.console.set_color_mode(False)

    def add_widget(self, widget: ConsoleWidget) -> None:
        self.widgets.append(widget)

    def add_widget_after(self, widget: ConsoleWidget, widget_on_list: ConsoleWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError as e:
            return False

        self.widgets.insert(idx + 1, widget)
        return True

    def add_widget_before(self, widget: ConsoleWidget, widget_on_list: ConsoleWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError as e:
            return False

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
    def __init__(self, x, y, button_state, control_key_state, event_flags):
        super().__init__()
        self.coordinates = (x, y)
        self.button_state = button_state
        self.control_key_state = control_key_state
        self.event_flags = event_flags


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
    def __init__(self):
        super().__init__()
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
        self.readConsoleInput = read_console_input_proto(('ReadConsoleInputW', self.kernel32), read_console_input_params)

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
            events_list.append(MouseEvent(x=record.Event.MouseEvent.dwMousePosition.X,
                                          y=record.Event.MouseEvent.dwMousePosition.Y,
                                          button_state=record.Event.MouseEvent.dwButtonState,
                                          control_key_state=record.Event.MouseEvent.dwControlKeyState,
                                          event_flags=record.Event.MouseEvent.dwEventFlags))
        elif record.EventType == self.KEY_EVENT:
            events_list.append(KeyEvent(key_down=record.Event.KeyEvent.bKeyDown,
                                        repeat_count=record.Event.KeyEvent.wRepeatCount,
                                        vk_code=record.Event.KeyEvent.wVirtualKeyCode,
                                        vs_code=record.Event.KeyEvent.wVirtualScanCode,
                                        char=record.Event.KeyEvent.uChar.AsciiChar,
                                        control_key_state=record.Event.KeyEvent.dwControlKeyState))
        else:
            pass

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


class Brush:
    def __init__(self, color=True):
        self.fgcolor = None
        self.bgcolor = None
        self.color = color

    RESET = '\x1B[0m'

    def color_mode(self):
        self.color = True

    def nocolor_mode(self):
        self.color = False

    def FgColor(self, color, check_last=False):
        if check_last:
            if self.fgcolor == color:
                return ''
        self.fgcolor = color
        if color is None:
            return ''
        return f'\x1B[38;5;{color}m'

    def BgColor(self, color, check_last=False):
        if check_last:
            if self.bgcolor == color:
                return ''
        self.bgcolor = color
        if color is None:
            return ''
        return f'\x1B[48;5;{color}m'

    def FgBgColor(self, color, check_last=False):
        ret_val = ''
        if (color[0] is None and self.fgcolor != color[0]) or (color[1] is None and self.bgcolor != color[1]):
            ret_val = self.ResetColor()
        ret_val += self.FgColor(color[0], check_last)
        ret_val += self.BgColor(color[1], check_last)
        return ret_val

    def print(self, *args, sep=' ', end='', file=None, fgcolor=None, bgcolor=None):
        if fgcolor is None and bgcolor is None:
            print(*args, sep=sep, end=end, file=file)
        else:
            color = (self.BgColor(bgcolor) if bgcolor else '') + (self.FgColor(fgcolor) if fgcolor else '')
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
    def MoveCursor(row: int = 1, column: int = 0):
        print(f'\x1B[{row};{column}H')

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
