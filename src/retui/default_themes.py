from enum import Enum, auto


class ThemePoint:
    TOP_LEFT = 0
    TOP = 1
    TOP_RIGHT = 2
    LEFT = 3
    MIDDLE = 4
    RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM = 7
    BOTTOM_RIGHT = 8


# TODO Two different imports, so we cant match it when using default theme - move defaulttheme to separate file
class DefaultThemesType(Enum):
    DOUBLE_TOP = auto()
    SIMPLE = auto()
    TEST = auto()
    DOUBLE_LINE = auto()
    SINGLE_LINE = auto()
    SINGLE_LINE_BOLD = auto()
    SINGLE_LINE_BOLD_CORNERS = auto()
    SINGLE_LINE_BOLD_TOP = auto()
    SINGLE_LINE_LIGHT_ROUNDED = auto()
    DOUBLE_TOP_ROUNDED_BOT = auto()


class DefaultThemes:
    predefined_borders = {
        # https://www.w3.org/TR/xml-entity-names/025.html
        DefaultThemesType.TEST: "012" "345" "678",
        DefaultThemesType.SIMPLE: "/-\\" "| |" "\\-/",
        DefaultThemesType.DOUBLE_TOP: "╒═╕" "│ │" "└─┘",
        DefaultThemesType.DOUBLE_LINE: "╔═╗" "║ ║" "╚═╝",
        DefaultThemesType.SINGLE_LINE: "┌─┐" "│ │" "└─┘",
        DefaultThemesType.SINGLE_LINE_BOLD_CORNERS: "┏─┓" "│ │" "┗─┛",
        DefaultThemesType.SINGLE_LINE_BOLD: "┏━┓" "┃ ┃" "┗━┛",
        DefaultThemesType.SINGLE_LINE_BOLD_TOP: "┍━┑" "│ │" "└─┘",
        DefaultThemesType.SINGLE_LINE_LIGHT_ROUNDED: "╭─╮" "│ │" "╰─╯",
        DefaultThemesType.DOUBLE_TOP_ROUNDED_BOT: "╒═╕" "│ │" "╰─╯",
    }

    default = DefaultThemesType.DOUBLE_TOP_ROUNDED_BOT

    @staticmethod
    def get_theme_border_str(default_theme: DefaultThemesType) -> str:
        return DefaultThemes.predefined_borders[default_theme]

    @staticmethod
    def get_default_theme_border_str() -> str:
        return DefaultThemes.predefined_borders[DefaultThemes.default]
