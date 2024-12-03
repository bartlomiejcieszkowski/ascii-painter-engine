import shutil
from abc import ABC, abstractmethod
from typing import Tuple

from retui.base import TerminalEvent


class SizeChangeEvent(TerminalEvent):
    def __init__(self):
        super().__init__()


class Terminal(ABC):
    def __init__(self, app, debug=True):
        # TODO: this would print without vt enabled yet update state if vt enabled in brush?
        self.app = app
        self.columns, self.rows = self.get_size()
        self.vt_supported = False
        self.debug = debug
        pass

    def update_size(self) -> Tuple[int, int]:
        # TODO CLEANUP HERE
        self.columns, self.rows = self.get_size()
        return self.columns, self.rows

    @staticmethod
    def get_size() -> Tuple[int, int]:
        columns, rows = shutil.get_terminal_size(fallback=(0, 0))
        # You can't use all lines, as it would move terminal 1 line down
        rows -= 1
        # OPEN: argparse does -2 for width
        # self.debug_print(f'{columns}x{rows}')
        return columns, rows

    def set_color_mode(self, enable: bool) -> bool:
        # TODO: careful with overriding
        self.vt_supported = enable
        return enable

    @abstractmethod
    def interactive_mode(self):
        pass

    @abstractmethod
    def read_events(self, callback, callback_ctx) -> bool:
        pass

    def set_title(self, title):
        if self.vt_supported:
            print(f"\033]2;{title}\007")

    def demo_mode(self):
        pass
