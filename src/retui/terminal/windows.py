import ctypes
import ctypes.wintypes
import msvcrt
import sys
from typing import Union

import retui.input_handling.windows
from retui.input_handling.windows import INPUT_RECORD
from retui.terminal.base import SizeChangeEvent, Terminal


class WindowsTerminal(Terminal):
    def __init__(self, app):
        super().__init__(app)
        self.kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
        set_console_mode_proto = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD)
        set_console_mode_params = (1, "hConsoleHandle", 0), (1, "dwMode", 0)
        self.setConsoleMode = set_console_mode_proto(("SetConsoleMode", self.kernel32), set_console_mode_params)

        get_console_mode_proto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL, ctypes.wintypes.HANDLE, ctypes.wintypes.LPDWORD
        )
        get_console_mode_params = (1, "hConsoleHandle", 0), (1, "lpMode", 0)
        self.getConsoleMode = get_console_mode_proto(("GetConsoleMode", self.kernel32), get_console_mode_params)
        self.consoleHandleOut = msvcrt.get_osfhandle(sys.stdout.fileno())
        self.consoleHandleIn = msvcrt.get_osfhandle(sys.stdin.fileno())

        read_console_input_proto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPVOID,  # PINPUT_RECORD
            ctypes.wintypes.DWORD,
            ctypes.wintypes.LPDWORD,
        )
        read_console_input_params = (
            (1, "hConsoleInput", 0),
            (1, "lpBuffer", 0),
            (1, "nLength", 0),
            (1, "lpNumberOfEventsRead", 0),
        )
        self.readConsoleInput = read_console_input_proto(
            ("ReadConsoleInputW", self.kernel32), read_console_input_params
        )

        get_number_of_console_input_events_proto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL, ctypes.wintypes.HANDLE, ctypes.wintypes.LPDWORD
        )
        get_number_of_console_input_events_params = (1, "hConsoleInput", 0), (
            1,
            "lpcNumberOfEvents",
            0,
        )
        self.getNumberOfConsoleInputEvents = get_number_of_console_input_events_proto(
            ("GetNumberOfConsoleInputEvents", self.kernel32),
            get_number_of_console_input_events_params,
        )
        self.blocking = True

    KEY_EVENT = 0x1
    MOUSE_EVENT = 0x2
    WINDOW_BUFFER_SIZE_EVENT = 0x4

    def interactive_mode(self):
        self.window_change_size_events(True)
        self.mouse_input(True)

    def blocking_input(self, blocking: bool):
        self.blocking = blocking

    def demo_mode(self):
        self.blocking_input(False)

    def read_console_input(self) -> Union[INPUT_RECORD, None]:
        record = retui.input_handling.windows.INPUT_RECORD()
        number_of_events = ctypes.wintypes.DWORD(0)
        if self.blocking is False:
            ret_val = self.getNumberOfConsoleInputEvents(self.consoleHandleIn, ctypes.byref(number_of_events))
            if number_of_events.value == 0:
                return None

        # TODO: N events
        ret_val = self.readConsoleInput(
            self.consoleHandleIn,
            ctypes.byref(record),
            1,
            ctypes.byref(number_of_events),
        )
        if ret_val == 0:
            return None
        return record

    def read_events(self, callback, callback_ctx) -> bool:
        events_list = []
        record = self.read_console_input()
        if record is None:
            pass
        elif record.EventType == self.WINDOW_BUFFER_SIZE_EVENT:
            events_list.append(SizeChangeEvent())
        elif record.EventType == self.MOUSE_EVENT:
            event = retui.input_handling.MouseEvent.from_windows_event(record.Event.MouseEvent)
            if event:
                events_list.append(event)
        elif record.EventType == self.KEY_EVENT:
            events_list.append(
                retui.input_handling.KeyEvent(
                    key_down=bool(record.Event.KeyEvent.bKeyDown),
                    repeat_count=record.Event.KeyEvent.wRepeatCount,
                    vk_code=record.Event.KeyEvent.wVirtualKeyCode,
                    vs_code=record.Event.KeyEvent.wVirtualScanCode,
                    char=record.Event.KeyEvent.uChar.AsciiChar,
                    wchar=record.Event.KeyEvent.uChar.UnicodeChar,
                    control_key_state=record.Event.KeyEvent.dwControlKeyState,
                )
            )
        else:
            pass

        if len(events_list):
            callback(callback_ctx, events_list)
        return True

    def get_console_mode(self, handle) -> int:
        dwMode = ctypes.wintypes.DWORD(0)
        # lpMode = ctypes.wintypes.LPDWORD(dwMode)
        # don't create pointer if not going to use it in python, use byref
        self.getConsoleMode(handle, ctypes.byref(dwMode))

        # print(f' dwMode: {hex(dwMode.value)}')
        return dwMode.value

    def set_console_mode(self, handle, mode: int):
        dwMode = ctypes.wintypes.DWORD(mode)
        self.setConsoleMode(handle, dwMode)
        return

    def set_mode(self, handle, mask: int, enable: bool) -> bool:
        console_mode = self.get_console_mode(handle)
        other_bits = mask ^ 0xFFFFFFFF
        expected_value = mask if enable else 0
        if (console_mode & mask) == expected_value:
            return True

        console_mode = (console_mode & other_bits) | expected_value
        self.set_console_mode(handle, console_mode)
        console_mode = self.get_console_mode(handle)
        return (console_mode & mask) == expected_value

    def set_virtual_terminal_processing(self, enable: bool) -> bool:
        # https://learn.microsoft.com/en-us/windows/console/high-level-console-modes
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4
        return self.set_mode(self.consoleHandleOut, ENABLE_VIRTUAL_TERMINAL_PROCESSING, enable)

    def set_color_mode(self, enable: bool) -> bool:
        success = self.set_virtual_terminal_processing(enable)
        return super().set_color_mode(enable & success)

    def window_change_size_events(self, enable: bool) -> bool:
        ENABLE_WINDOW_INPUT = 0x8
        return self.set_mode(self.consoleHandleIn, ENABLE_WINDOW_INPUT, enable)

    def set_quick_edit_mode(self, enable: bool) -> bool:
        ENABLE_QUICK_EDIT_MODE = 0x40
        return self.set_mode(self.consoleHandleIn, ENABLE_QUICK_EDIT_MODE, enable)

    def mouse_input(self, enable: bool) -> bool:
        # Quick Edit Mode blocks mouse events
        self.set_quick_edit_mode(False)
        ENABLE_MOUSE_INPUT = 0x10
        return self.set_mode(self.consoleHandleIn, ENABLE_MOUSE_INPUT, enable)
