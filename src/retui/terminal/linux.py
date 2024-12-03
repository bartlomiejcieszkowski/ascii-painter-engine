import fcntl
import logging
import os
import signal
import sys
import termios

import retui.input_handling
from retui.terminal.base import SizeChangeEvent, Terminal

_log = logging.getLogger(__name__)


class LinuxTerminal(Terminal):
    def __init__(self, app):
        super().__init__(app)
        self.is_interactive_mode = False
        self.window_changed = False
        self.prev_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        new_fl = self.prev_fl | os.O_NONBLOCK
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, new_fl)
        _log.debug(f"stdin fl: 0x{self.prev_fl:X} -> 0x{new_fl:X}")
        self.prev_tc = termios.tcgetattr(sys.stdin)
        new_tc = termios.tcgetattr(sys.stdin)
        # manipulating lflag
        new_tc[3] = new_tc[3] & ~termios.ECHO  # disable input echo
        new_tc[3] = new_tc[3] & ~termios.ICANON  # disable canonical mode - input available immediately
        # cc
        # VMIN | VTIME | Result
        # =0   | =0    | non-blocking read
        # =0   | >0    | timed read
        # >0   | >0    | timer started on 1st char read
        # >0   | =0    | counted read
        new_tc[6][termios.VMIN] = 0
        new_tc[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_tc)  # TCSADRAIN?
        _log.debug(f"stdin lflags: 0x{self.prev_tc[3]:X} -> 0x{new_tc[3]:X}")
        _log.debug(f"stdin cc VMIN: 0x{self.prev_tc[6][termios.VMIN]} -> 0x{new_tc[6][termios.VMIN]}")
        _log.debug(f"stdin cc VTIME: 0x{self.prev_tc[6][termios.VTIME]} -> 0x{new_tc[6][termios.VTIME]}")

        self.input_interpreter = retui.input_handling.InputInterpreter(sys.stdin)

    def __del__(self):
        # restore stdin
        if self.is_interactive_mode:
            print("\x1B[?10001")

        termios.tcsetattr(sys.stdin, termios.TCSANOW, self.prev_tc)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self.prev_fl)
        print("xRestore console done")
        if self.is_interactive_mode:
            print("\x1B[?1006l\x1B[?1015l\x1B[?1003l")
        # where show cursor?

    window_change_event_ctx = None

    @staticmethod
    def window_change_handler(signum, frame):
        LinuxTerminal.window_change_event_ctx.window_change_event()

    def window_change_event(self):
        # inject special input on stdin?
        self.window_changed = True

    def interactive_mode(self):
        self.is_interactive_mode = True
        LinuxTerminal.window_change_event_ctx = self
        signal.signal(signal.SIGWINCH, LinuxTerminal.window_change_handler)
        # ctrl-z not allowed
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        # enable mouse - xterm, sgr1006
        print("\x1B[?1003h\x1B[?1006h")
        # focus event
        # CSI I on focus
        # CSI O on loss
        print("\x1B[?1004h")

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
