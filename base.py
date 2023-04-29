from enum import IntEnum
from typing import Union


class ColorBits(IntEnum):
    Bit8 = 5
    Bit24 = 2


class Color:
    def __init__(self, color: int, bits: ColorBits):
        self.color = color
        self.bits = bits


class ConsoleColor:
    def __init__(
        self, fgcolor: Union[Color, None] = None, bgcolor: Union[Color, None] = None
    ):
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor

    def no_color(self):
        return self.fgcolor is None and self.bgcolor is None


class Point:
    def __init__(self, c: str = " ", color: ConsoleColor = ConsoleColor()):
        self.c = c
        self.color = color
