from enum import Flag, IntEnum


class TabIndex:
    # tab_index:
    # -1 - not selectable TODO
    TAB_INDEX_NOT_SELECTABLE = -1
    # -2 - auto - parent would go from top-left line by line and auto assign tab index TODO
    TAB_INDEX_AUTO = -2


class Alignment(Flag):
    Center = 0
    Left = 1
    Right = 2
    Top = 4
    Bottom = 8
    TopLeft = Left | Top
    TopRight = Right | Top
    BottomLeft = Left | Bottom
    BottomRight = Right | Bottom
    Float = 16
    FloatTopLeft = Float | TopLeft
    FloatTopRight = Float | TopRight
    FloatBottomLeft = Float | BottomLeft
    FloatBottomRight = Float | BottomRight
    FloatLeft = Float | Left
    FloatRight = Float | Right
    FloatTop = Float | Top
    FloatBottom = Float | Bottom


class DimensionsFlag(Flag):
    Absolute = 0
    RelativeWidth = 1
    RelativeHeight = 2
    Relative = RelativeWidth | RelativeHeight
    FillWidth = 4
    FillHeight = 8
    Fill = FillWidth | FillHeight
    FillWidthRelativeHeight = FillWidth | RelativeHeight
    FillHeightRelativeWidth = FillHeight | RelativeWidth


class TextAlign(IntEnum):
    # bYYXX
    # isTop = value & 0xC == 0x0, middle &0xC == 0x4, bottom &0xC ==0x8
    # isLeft = value & 0x3 == 0x0, center &0x3 == 0x1, right &0x3 == 0x2
    TopLeft = 0x0
    TopCenter = 0x1
    TopRight = 0x2
    MiddleLeft = 0x4
    MiddleCenter = 0x5
    MiddleRight = 0x6
    BottomLeft = 0x8
    BottomCenter = 0x9
    BottomRight = 0xA

    def is_top(self):
        return self.value & 0xC == 0x0

    def is_middle(self):
        return self.value & 0xC == 0x4

    def is_bottom(self):
        return self.value & 0xC == 0x8

    def is_left(self):
        return self.value & 0x3 == 0x0

    def is_center(self):
        return self.value & 0x3 == 0x1

    def is_right(self):
        return self.value & 0x3 == 0x2


class WordWrap(IntEnum):
    Trim = 0
    Wrap = 1
    WrapWordEnd = 2
