import shutil

# Notes:
# You can have extra line of console, which wont be fully visible - as w/a just dont use last line
# If new size is greater, then fill with new lines so we wont be drawing in the middle of screen

import ctypes
import ctypes.wintypes
import msvcrt
import sys

from enum import Enum, auto
from abc import ABC, abstractmethod


import os

def is_windows() -> bool:
    return os.name == 'nt'

class ConsoleBuffer:
    def __init__(self):
        pass

    @staticmethod
    def fill_buffer(x, y, symbol=' '):
        return ('\n' + (symbol*x)) * y


class ConsoleWidgetAlignment(Enum):
    LEFT_TOP = auto()
    RIGHT_TOP = auto()
    LEFT_BOTTOM = auto()
    RIGHT_BOTTOM = auto()


class ConsoleWidget(ABC):
    def __init__(self, x: int, y: int, width: int, height: int, alignment: ConsoleWidgetAlignment):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.alignment = alignment

    @abstractmethod
    def draw(self):
        pass


class ConsoleWidgets:
    class TextBox(ConsoleWidget):
        def __init__(self, text: str, x: int, y: int, width: int, height: int, alignment: ConsoleWidgetAlignment):
            super().__init__(x=x, y=y, width=width, height=height, alignment=alignment)
            self.text = text

        def draw(self):
            pass


class Console:
    def __init__(self, debug=True):
        self.brush = Brush(self)
        self.debug = debug
        self.debug_colors = (None, None) # 14, 4
        # TODO: this would print without vt enabled yet update state if vt enabled in brush?
        self.size = self.get_size()
        self.vt_supported = False

        pass

    def update_size(self):
        self.size = self.get_size()

    def get_size(self):
        terminal_size = shutil.get_terminal_size(fallback=(0, 0))
        #self.debug_print(f'{terminal_size[0]}x{terminal_size[1]}')
        return terminal_size

    def debug_print(self, text, end='\n'):
        if self.debug:
            self.brush.print(text, fgcolor=self.debug_colors[0], bgcolor=self.debug_colors[1], end=end)

    def set_color_mode(self, enable:bool):
        if enable:
            self.vt_supported = True
            self.debug_colors = (14, 4)
        else:
            self.vt_supported = False
            self.debug_colors = (None, None)
        return enable

    def clear(self, reuse=True):
        self.update_size()
        if reuse:
            self.brush.MoveCursor(1, 1)
        print(ConsoleBuffer.fill_buffer(self.size[0], self.size[1], ' '), end='')

    @abstractmethod
    def interactive_mode(self):
        pass

    @abstractmethod
    def read_events(self, callback, callback_ctx) -> list:
        pass


class LinuxConsole(Console):
    # TODO
    def __init__(self):
        super().__init__()



class ConsoleView:
    def __init__(self):
        if is_windows():
            self.console = WindowsConsole()
        else:
            self.console = LinuxConsole()
        self.widgets = []

    @staticmethod
    def handle_events_callback(ctx, events_list):
        ctx.handle_events(events_list)

    def handle_events(self, events_list):
        pass

    def loop(self) -> int:
        self.console.update_size()

        # create blank canvas
        self.console.clear(reuse=False)

        self.console.interactive_mode()

        i = 0
        while self.console.read_events(self.handle_events_callback, self):
            i += 1

    def color_mode(self) -> bool:
        return self.console.set_color_mode(True)

    def nocolor_mode(self) -> bool:
        return self.console.set_color_mode(False)

    def add_widget(self, widget: ConsoleWidget) -> None:
        self.widgets.append(widget)

    def add_widget_after(self, widget: ConsoleWidget, widget_on_list: ConsoleWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError as e:
            return False

        self.widgets.insert(idx+1)
        return True

    def add_widget_before(self, widget: ConsoleWidget, widget_on_list: ConsoleWidget) -> bool:
        try:
            idx = self.widgets.index(widget_on_list)
        except ValueError as e:
            return False

        self.widgets.insert(idx)
        return True
    # TODO: register for console size change

class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.wintypes.SHORT),
                ("Y", ctypes.wintypes.SHORT)]

class MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("dwMousePosition", COORD),
                ("dwButtonState", ctypes.wintypes.DWORD),
                ("dwControlKeyState", ctypes.wintypes.DWORD),
                ("dwEventFlags", ctypes.wintypes.DWORD)]

class INPUT_RECORD_Event(ctypes.Union):
    _fields_ = [("KeyEvent", ctypes.c_uint),
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


class WindowsConsole(Console):
    def __init__(self):
        super().__init__()
        self.kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        setConsoleModeProto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD
        )
        setConsoleModeParams = (1, "hConsoleHandle", 0), (1, "dwMode", 0)
        self.setConsoleMode = setConsoleModeProto(('SetConsoleMode', self.kernel32), setConsoleModeParams)

        getConsoleModeProto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPDWORD
        )
        getConsoleModeParams = (1, "hConsoleHandle", 0), (1, "lpMode", 0)
        self.getConsoleMode = getConsoleModeProto(('GetConsoleMode', self.kernel32), getConsoleModeParams)
        self.consoleHandleOut = msvcrt.get_osfhandle(sys.stdout.fileno())
        self.consoleHandleIn = msvcrt.get_osfhandle(sys.stdin.fileno())

        readConsoleInputProto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPVOID, # PINPUT_RECORD
            ctypes.wintypes.DWORD,
            ctypes.wintypes.LPDWORD
        )
        readConsoleInputParams = (1, "hConsoleInput", 0), (1, "lpBuffer", 0), (1, "nLength", 0), (1, "lpNumberOfEventsRead", 0)
        self.readConsoleInput = readConsoleInputProto(('ReadConsoleInputW', self.kernel32), readConsoleInputParams)

    MOUSE_EVENT = 0x2
    WINDOW_BUFFER_SIZE_EVENT = 0x4

    def interactive_mode(self):
        self.SetWindowChangeSizeEvents(True)
        self.SetMouseInput(True)

    def read_events(self, callback, callback_ctx) -> list:
        events_list = []
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
        else:
            pass

        callback(callback_ctx, events_list)
        return True

    def GetConsoleMode(self, handle) -> int:
        dwMode = ctypes.wintypes.DWORD(0)
        # lpMode = ctypes.wintypes.LPDWORD(dwMode)
        # dont create pointer if not going to use it in python, use byref
        self.getConsoleMode(handle, ctypes.byref(dwMode))

        # print(f' dwMode: {hex(dwMode.value)}')
        return dwMode.value

    def SetConsoleMode(self, handle, mode: int):
        dwMode = ctypes.wintypes.DWORD(mode)
        self.setConsoleMode(handle, dwMode)
        return

    def SetMode(self, handle, mask: int, enable: bool) -> bool:
        consoleMode = self.GetConsoleMode(handle)
        other_bits = mask ^ 0xFFFFFFFF
        expected_value = mask if enable else 0
        if (consoleMode & mask) == expected_value:
            return True

        consoleMode = (consoleMode & other_bits) | expected_value
        self.SetConsoleMode(handle, consoleMode)
        consoleMode = self.GetConsoleMode(handle)
        return (consoleMode & mask) == expected_value

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
    def __init__(self, console=None):
        self.fgcolor = None
        self.bgcolor = None
        self.console = console

    RESET = '\x1B[0m'

    def FgColor(self, color):
        return f'\x1B[38;5;{color}m'

    def BgColor(self, color):
        return f'\x1B[48;5;{color}m'

    def print(self, *args, sep=' ', end='\n', file=None, fgcolor=None, bgcolor=None):
        if fgcolor is None and bgcolor is None:
            print(*args, sep=sep, end=end, file=file)
        else:
            color = (self.BgColor(bgcolor) if bgcolor else '') + (self.FgColor(fgcolor) if fgcolor else '')
            print(color+" ".join(map(str, args))+self.RESET, sep=sep, end=end, file=file)

    def SetFgColor(self, color):
        print(self.FgColor(color), end='')

    def SetBgColor(self, color):
        print(self.BgColor(color), end='')

    def Reset(self):
        print(self.RESET, end='')

    def MoveUp(self, lines):
        print(f'\x1B[{lines}F')

    def MoveDown(self, lines):
        print(f'\x1B[{lines}E')

    def MoveColumn(self, column):
        print(f'\x1B[{column}G')

    def MoveCursor(self, row, column):
        print(f'\x1B[{row};{column}H')

class Test:
    @staticmethod
    def ColorLine(start, end, text='  ', use_color=False, width=2):
        for color in range(start, end):
            print(f'\x1B[48;5;{color}m{("{:"+ str(width) + "}").format(color) if use_color else text}', end='')
        print('\x1B[0m')

    @staticmethod
    def ColorLine24bit(start,end,step=0):
        for color in range(start, end, step):
            print(f'\x1B[48;2;{color};{color};{color}mXD', end='')
        print('\x1B[0m')


def main():
    console_view = ConsoleView()
    console_view.color_mode()

    widget = ConsoleWidgets.TextBox(text='Test', x=2, y=2, height=4, width=10, alignment=ConsoleWidgetAlignment.LEFT_TOP)

    console_view.add_widget(widget)
    console_view.loop()


def test():
    wc = WindowsConsole()
    success = wc.set_color_mode(True)
    print(f'EnableVT? {success}')
    if not success:
        print('Abort')
        return
    print("\x1B[34m" + 'TEST 8bit ANSII Codes' + "\x1B[0m")
    Test.ColorLine(0, 8, use_color=True, width=2)
    Test.ColorLine(8, 16, use_color=True, width=2)
    for red in range(0, 6):
        start = 16 + 6 * 6 * red
        end = start + 36
        Test.ColorLine(start, end, use_color=True, width=3)

    Test.ColorLine(232, 256, use_color=True, width=4)

    brush = Brush()

    brush.SetBgColor(4)
    brush.SetFgColor(14)
    print("TEST", end='')
    brush.Reset()
    print()

    brush.print("TEST", fgcolor=14, bgcolor=4)

    wc.update_size()
    # create blank canvas
    print(ConsoleBuffer.fill_buffer(wc.size[0], wc.size[1]))
    wc.SetWindowChangeSizeEvents(True)
    wc.SetMouseInput(True)
    i = 0
    while wc.read_events(None, None):
        #print(f'in: {hex(wc.GetConsoleMode(wc.consoleHandleIn))}')
        #print(f'out: {hex(wc.GetConsoleMode(wc.consoleHandleOut))}')
        i += 1
    #for i in range(0,255):
    #   Test.ColorLine24bit(16*i, 16*(i+1),1)

    # TODO:
    # CMD - mouse coordinates include a big buffer scroll up, so instead of 30 we get 1300 for y-val
    # Windows Terminal - correct coord

    # BUG Windows Terminal
    # CMD - generates EventType 0x10 on focus or loss with ENABLE_QUICK_EDIT_MODE
    # Terminal - nothing
    # without quick edit mode the event for focus loss is not raised
    # however this is internal event and should be ignored according to msdn


if __name__ == '__main__':
    #test()
    main()
