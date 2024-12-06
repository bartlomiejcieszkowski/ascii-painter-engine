from abc import ABC
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Tuple, Union

import retui.enums


class ColorBits(IntEnum):
    BIT_8 = 5
    BIT_24 = 2
    BIT_NONE = 0


@dataclass
class Color:
    color: int
    bits: ColorBits

    @classmethod
    def default(cls):
        return cls(-1, ColorBits.BIT_NONE)

    def none(self):
        return self.bits == ColorBits.BIT_NONE


@dataclass()
class TerminalColor:
    foreground: Color = field(default_factory=Color.default)
    background: Color = field(default_factory=Color.default)

    @classmethod
    def default(cls):
        return cls()

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
        self.foreground = Color.default()
        self.background = Color.default()

    def __iadd__(self, other):
        self.foreground = other.foreground if other.foreground else self.foreground
        self.background = other.background if other.background else self.background
        return self


@dataclass
class Point:
    c: str = " "
    color: TerminalColor = field(default_factory=TerminalColor.default)


@dataclass
class Rectangle:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def x_end(self):
        return self.x + self.width

    def y_end(self):
        return self.y + self.height

    def update(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        # TODO: possibility to return has it changed?

    def update_tuple(self, dimensions: Union[Tuple[int, int, int, int], List]):
        self.x = dimensions[0]
        self.y = dimensions[1]
        self.width = dimensions[2]
        self.height = dimensions[3]

    def contains_point(self, x: int, y: int):
        return not ((self.y > y) or (self.y + self.height - 1 < y) or (self.x > x) or (self.x + self.width - 1 < x))

    def translate_coordinates(self, parent):
        # TODO what if initial position is overflowing?
        self.x += parent.x
        self.y += parent.y
        # on parent overflow, trim to it size
        self.width = self.width if self.x_end() <= parent.x_end() else self.width + (parent.x_end() + self.x_end())
        self.height = self.height if self.y_end() <= parent.y_end() else self.height + (parent.y_end() + self.y_end())

    def negative(self):
        return self.x < 0 or self.y < 0 or self.width < 0 or self.height < 0


class TerminalEvent(ABC):
    def __init__(self):
        pass


def json_convert(key, value):
    # TODO capitalize?
    if key == "dock":
        if isinstance(value, retui.enums.Dock):
            return value
        if value is None:
            value = "NONE"
        value = retui.enums.Dock[value]
    elif key == "dimensions":
        if isinstance(value, retui.enums.DimensionsFlag):
            return value
        if value is None:
            value = "ABSOLUTE"
        value = retui.enums.DimensionsFlag[value]
    elif key == "text_align":
        if isinstance(value, retui.enums.TextAlign):
            return value
        if value is None:
            value = "TOP_LEFT"
        value = retui.enums.TextAlign[value]
    elif key == "text_wrap":
        if isinstance(value, retui.enums.WordWrap):
            return value
        if value is None:
            value = "WRAP"
        value = retui.enums.WordWrap[value]
    return value
