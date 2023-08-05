from enum import IntEnum
from typing import Union


class ColorBits(IntEnum):
    Bit8 = 5
    Bit24 = 2


class Color:
    def __init__(self, color: int, bits: ColorBits):
        self.color = color
        self.bits = bits

    def __str__(self):
        return f"Color(0x{self.color:X}, {self.bits.name})"

    def __eq__(self, other):
        return isinstance(other, Color) and self.bits == other.bits and self.color == other.color


class ConsoleColor:
    def __init__(self, foreground: Union[Color, None] = None, background: Union[Color, None] = None):
        self.foreground = foreground
        self.background = background

    def update_foreground(self, color: Color) -> bool:
        if self.foreground == color:
            return False
        self.foreground = color
        return True

    def update_background(self, color: Color) -> bool:
        if self.background == color:
            return False
        self.background = color
        return True

    def no_color(self):
        return self.foreground is None and self.background is None

    def reset(self):
        self.foreground = None
        self.background = None

    def __str__(self):
        return f"ConsoleColor({self.foreground}, {self.background})"

    def __eq__(self, other):
        return (
            isinstance(other, ConsoleColor)
            and self.foreground == other.foreground
            and self.background == other.background
        )


class Point:
    def __init__(self, c: str = " ", color: ConsoleColor = ConsoleColor()):
        self.c = c
        self.color = color
