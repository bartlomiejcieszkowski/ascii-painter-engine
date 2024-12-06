from enum import Enum, Flag, IntEnum, auto


class TabIndex:
    # tab_index:
    # -1 - not selectable TODO
    TAB_INDEX_NOT_SELECTABLE = -1
    # -2 - auto - parent would go from top-left line by line and auto assign tab index TODO
    TAB_INDEX_AUTO = -2


# Winforms have:
# Behavior:
# TabIndex - int
# TabStop - True -> can select with tab
# Enabled - bool
# Visible - bool
# Layout:
# Dock -> None, Top, Bottom, Left, Right, Fill
# AutoSize - boolean
# AutoSizeMode - GrowOnly, GrowAndShrink
# Anchor -> Top / Bottom / Left / Right - can be all.. why


class Dock(Enum):
    NONE = auto()
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    FILL = auto()


class DimensionsFlag(Flag):
    ABSOLUTE = 0
    RELATIVE_WIDTH = 1
    RELATIVE_HEIGHT = 2
    RELATIVE = RELATIVE_WIDTH | RELATIVE_HEIGHT
    FILL_WIDTH = 4
    FILL_HEIGHT = 8
    FILL = FILL_WIDTH | FILL_HEIGHT
    FILL_WIDTH_RELATIVE_HEIGHT = FILL_WIDTH | RELATIVE_HEIGHT
    RELATIVE_HEIGHT_FILL_WIDTH = FILL_WIDTH_RELATIVE_HEIGHT
    FILL_HEIGHT_RELATIVE_WIDTH = FILL_HEIGHT | RELATIVE_WIDTH
    RELATIVE_WIDTH_FILL_HEIGHT = FILL_HEIGHT_RELATIVE_WIDTH


class TextAlign(IntEnum):
    # bYYXX
    # isTop = value & 0xC == 0x0, middle &0xC == 0x4, bottom &0xC ==0x8
    # isLeft = value & 0x3 == 0x0, center &0x3 == 0x1, right &0x3 == 0x2
    TOP_LEFT = 0x0
    TOP_CENTER = 0x1
    TOP_RIGHT = 0x2
    MIDDLE_LEFT = 0x4
    MIDDLE_CENTER = 0x5
    MIDDLE_RIGHT = 0x6
    BOTTOM_LEFT = 0x8
    BOTTOM_CENTER = 0x9
    BOTTOM_RIGHT = 0xA

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
    TRIM = 0
    WRAP = 1
    WRAP_WORD_END = 2
