from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from os import PathLike
from typing import Union

from retui.base import Color, ColorBits, Point, TerminalColor
from retui.default_themes import DefaultThemes
from retui.utils.strings import StringHelper


@dataclass
class Selector:
    element_name: str
    element_id: str
    element_classes: list[str]


def css_color_to_color(string: str):
    # case of #aabbcc !important
    text = string.split(" ")[0]
    value = None

    if text.startswith("#"):
        value = int(text[1:], 16)
    elif text.startswith("rgb(") and text.endswith(")"):
        split_rgb = text[4:-1].split(",")
        if len(split_rgb) == 3:
            r = int(split_rgb[0])
            g = int(split_rgb[1])
            b = int(split_rgb[2])
            value = b & 0xFF + ((g & 0xFF) << 8) + ((r & 0xFF) << 16)

    if value:
        return Color(value, ColorBits.Bit24)
    return None


@dataclass
class Attributes:
    color: TerminalColor = field(default_factory=TerminalColor.default)

    def __iadd__(self, other):
        self.color += other.color
        return self

    @staticmethod
    def handle_background_color(this, prop, value):
        pass

    @staticmethod
    def handle_color(this, prop, value):
        pass

    @classmethod
    def from_prop(cls, prop: str, value: str):
        color = TerminalColor.default()
        if prop == "background-color":
            single_color = css_color_to_color(value)
            if single_color:
                color = TerminalColor(background=single_color)
        elif prop == "color":
            single_color = css_color_to_color(value)
            if single_color:
                color = TerminalColor(foreground=single_color)
        return cls(color=color)


class Selectors(ABC):
    class Type(Enum):
        Universal = auto()
        Element = auto()
        Id = auto()
        Class = auto()
        # ElementClass = auto()
        Unsupported = auto()

        @classmethod
        def from_name(cls, name: str):
            if name == "*":
                return cls.Universal
            elif name.startswith("#"):
                return cls.Id
            elif name.startswith("."):
                return cls.Class
            # place to log
            return cls.Unsupported

    property_handlers = {
        "background-color": Attributes.handle_background_color,
        "color": Attributes.handle_color,
    }

    def __init__(self):
        # selectors are inspired by css
        # TODO: allow styling by css stylesheet, but with limited subset
        self.selectors = {}
        self.id_selectors = {}
        self.class_selectors = {}
        self.universal_selector = None

    def add_property(self, selectors: Union[str, list[str]], prop: str, value: str):
        if selectors is str:
            # single selector
            selectors = [selectors]

        for selector in selectors:
            if " " in selector:
                # "div p" unsupported
                continue
            # div p, div -> ["div p", "div"] so if we were to handle them properly it is still some parsing to do
            print(f"adding: {selector} {{ {prop}: {value}; }}")
            selector_type = self.Type.from_name(selector)
            if selector_type == self.Type.Unsupported:
                continue
            attributes = Attributes.from_prop(prop, value)
            if attributes is None:
                continue
            self.add_selector(selector_type, selector, attributes)

    def add_selector(self, selector_type: Type, name: str, attributes):
        if attributes is None:
            print(f"invalid selector - {selector_type} {name} - attributes: {attributes}")
            return
        try:
            if selector_type == self.Type.Universal:
                if self.universal_selector is None:
                    self.universal_selector = attributes
                else:
                    self.universal_selector += attributes
            elif selector_type == self.Type.Id:
                selector_attributes = self.id_selectors.get(name)
                if selector_attributes:
                    selector_attributes += attributes
                else:
                    selector_attributes = attributes
                self.id_selectors[name] = selector_attributes
            elif selector_type == self.Type.Class:
                selector_attributes = self.class_selectors.get(name)
                if selector_attributes:
                    selector_attributes += attributes
                else:
                    selector_attributes = attributes
                self.class_selectors[name] = selector_attributes
            elif selector_type == self.Type.Element:
                selector_attributes = self.selectors.get(name)
                if selector_attributes:
                    selector_attributes += attributes
                else:
                    selector_attributes = attributes
                self.selectors[name] = selector_attributes
            else:
                pass
        except Exception as e:
            print(f"Exception {selector_type}, {name}, {attributes}")
            raise e

    def effective_selector(self, selector: Selector):
        none_attributes = Attributes()
        attributes = Attributes()
        attributes += self.universal_selector
        attributes += self.selectors.get(selector.element_name, none_attributes)
        for name in selector.element_classes:
            attributes += self.class_selectors.get(name, none_attributes)
        attributes += self.id_selectors.get(selector.element_id, none_attributes)
        return attributes

    def __str__(self):
        return "selectors: \n\t{}\nid_selectors: \n\t{}\nclass_selectors: \n\t{}\nuniversal_selector: \n\t{}\n".format(
            "\n\t".join(self.selectors),
            "\n\t".join(self.id_selectors),
            "\n\t".join(self.class_selectors),
            self.universal_selector,
        )


class CssParserState(IntEnum):
    selector = 0
    open_sect = 1
    property = 2
    value = 3
    colon = 4
    semi_colon = 5
    comment = 6


class CssParser:
    # TODO: properly handle nested { {
    # https://www.w3.org/TR/css-syntax-3/#parsing-overview

    @staticmethod
    def parse(file_name: PathLike[str], selectors: Union[Selectors, None]) -> Selectors:
        if selectors is None:
            selectors = Selectors()
        with open(file_name, "r") as f:
            last_state = CssParserState.selector
            state = CssParserState.selector
            selector = None
            prop = None
            failed = None
            line_num = 0
            word = ""
            non_printables = ["\n", "\r", "\t"]
            for line in f:
                line_num += 1
                idx = 0
                end = len(line)
                while idx < end:
                    c = line[idx]
                    # big switch goes here
                    if state == CssParserState.comment:
                        if c == "*":
                            # hope
                            if idx + 1 < end:
                                c_next = line[idx + 1]
                                if c_next == "/":
                                    # comment end
                                    # restore state and skip */
                                    state = last_state
                                    idx += 2
                                    continue
                        idx += 1
                        continue

                    if c == "/":
                        # comment?
                        if idx + 1 < end:
                            # comment can't span to next line
                            c_next = line[idx + 1]
                            if c_next == "*":
                                # comment start
                                # store state and skip /*
                                last_state = state
                                state = CssParserState.comment
                                idx += 2
                                continue

                    if c in non_printables:
                        c = " "

                    if state == CssParserState.selector:
                        if len(word) > 0:
                            if c == "{":
                                # '*{'
                                #   ^
                                state = CssParserState.open_sect
                                # omit increment - we will hit the switch for {
                                continue
                            # elif c != ' ':
                            #    word += c
                            else:
                                # we will have all words, need to split them later
                                word += c
                                # state = State.open_sect
                        elif c == " ":
                            # optimization
                            # '    * {'
                            #  ^^^^
                            pass
                        else:
                            # '    * {'
                            #      ^
                            word += c
                        idx += 1
                        continue
                    elif state == CssParserState.open_sect:
                        # if c == ' ':
                        #
                        #    # skipping spaces
                        #    pass
                        if c == "{":
                            selector = word
                            word = ""
                            state = CssParserState.property
                            pass
                        else:
                            failed = Exception(f'{line_num}: state: {state} - got "{c}" - line: "{line}"')
                            break
                        idx += 1
                        continue
                    elif state == CssParserState.property:
                        if c == ":":
                            state = CssParserState.colon
                            continue
                        elif c == "}":
                            # reset word
                            word = ""
                            state = CssParserState.selector
                        # elif c == ' ':
                        #     # yes, i know that this will remove spaces
                        #     pass
                        else:
                            word += c
                        idx += 1
                        continue
                    elif state == CssParserState.colon:
                        if c == ":":
                            prop = word
                            word = ""
                            state = CssParserState.value
                        # elif c == ' ':
                        #    pass
                        else:
                            failed = Exception(f'{line_num}: state: {state} - got "{c}" - line: "{line}"')
                            break
                        idx += 1
                        continue
                    elif state == CssParserState.value:
                        # if c == ' ':
                        #    pass
                        if c == ";":
                            state = CssParserState.semi_colon
                            continue
                        else:
                            word += c
                        idx += 1
                        continue
                    elif state == CssParserState.semi_colon:
                        if c == ";":
                            value = word
                            word = ""
                            state = CssParserState.property
                            prop = " ".join(prop.split())
                            value = " ".join(value.split())
                            selector_split = StringHelper.split_trim(selector, ",")
                            selectors.add_property(selector_split, prop, value)
                        # elif c == ' ':
                        #    pass
                        else:
                            failed = Exception(f'{line_num}: state: {state} - got "{c}" - line: "{line}"')
                            break
                        idx += 1
                        continue
                    else:
                        failed = Exception(f"UNHANDLED STATE: {state}")
                        break
                if failed:
                    break

            if failed:
                # cleanup goes here
                raise failed

        return selectors


class Theme:
    class Colors:
        def __init__(self):
            self.text = TerminalColor(Color(0, ColorBits.Bit24))

        @classmethod
        def monokai(cls):
            # cyan = 0x00B9D7
            # gold_brown = 0xABAA98
            # green = 0x82CDB9
            # off_white = 0xF5F5F5
            # orange = 0xF37259
            # pink = 0xFF3D70
            # pink_magenta = 0xF7208B
            # yellow = 0xF9F5C2
            pass

    def __init__(self, border: list[Point]):
        # border string
        # 155552
        # 600007
        # 600007
        # 388884
        # where the string is in form
        # '012345678'

        # validate border
        self.border = []
        if len(border) >= 9:
            for i in range(0, 9):
                if not isinstance(border[i], Point):
                    break
                self.border.append(border[i])

        if len(self.border) < 9:
            # invalid border TODO
            self.border = 9 * [Point(" ")]

        self.selectors = Selectors()

    def set_color(self, color):
        for i in range(0, 9):
            self.border[i].color = color

    def border_inside_set_color(self, color):
        self.border[0].color = color

    @staticmethod
    def border_from_str(border_str: str) -> list[Point]:
        border = []
        if len(border_str) < 9:
            raise Exception(f"border_str must have at least len of 9 - got {len(border_str)}")
        for i in range(0, 9):
            border.append(Point(border_str[i]))
        return border

    @classmethod
    def default_theme(cls):
        return cls(border=_DEFAULT_THEME_BORDER)


_DEFAULT_THEME_BORDER = Theme.border_from_str(DefaultThemes.get_default_theme_border_str())
_APP_THEME = Theme.default_theme()
