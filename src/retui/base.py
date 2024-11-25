from dataclasses import dataclass, field
from enum import IntEnum


class ColorBits(IntEnum):
    Bit8 = 5
    Bit24 = 2
    BitNone = 0


@dataclass
class Color:
    color: int
    bits: ColorBits

    @classmethod
    def default(cls):
        return cls(-1, ColorBits.BitNone)

    def none(self):
        return self.bits == ColorBits.BitNone


@dataclass()
class ConsoleColor:
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
    color: ConsoleColor = field(default_factory=ConsoleColor.default)
