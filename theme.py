from abc import ABC
from enum import Enum, IntEnum, auto

from ascii_painter_engine import Color, ColorBits, ConsoleColor


class Selector:
    def __init__(self, element_name: str, element_id: str, element_classes: list[str]):
        self.element_name = element_name
        self.element_id = element_id
        self.element_classes = element_classes


def CssColorToColor(text: str):
    value = None
    try:
        if text.startswith("#"):
            value = int(text[1:], 16)
        elif text.endswith(")"):
            if text.startswith("rgb("):
                r, g, b = text[4:-1].split(",")
                r = int(r)
                g = int(g)
                b = int(b)
                value = b & 0xFF + ((g & 0xFF) << 8) + ((r & 0xFF) << 16)
    except Exception:
        value = None
    if value:
        return Color(value, ColorBits.Bit24)
    return None


class Attributes:
    def __init__(self, color: ConsoleColor = None):
        if color:
            self.color = color
        else:
            self.color = ConsoleColor(fgcolor=None, bgcolor=None)

    def add(self, other):
        if other.color.fgcolor is not None:
            self.color.fgcolor = other.color.fgcolor
        if other.color.bgcolor is not None:
            self.color.bgcolor = other.color.bgcolor

    def __str__(self):
        return f"Attributes({self.color})"

    @staticmethod
    def handle_background_color(this, prop, value):
        pass

    @staticmethod
    def handle_color(this, prop, value):
        pass

    @classmethod
    def from_prop(cls, prop: str, value: str):
        color = None
        if prop == "background-color":
            single_color = CssColorToColor(value)
            if single_color:
                color = ConsoleColor(fgcolor=None, bgcolor=single_color)
        elif prop == "color":
            single_color = CssColorToColor(value)
            if single_color:
                color = ConsoleColor(fgcolor=single_color, bgcolor=None)
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

    def add_property(self, selectors: str, prop: str, value: str):
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
            print(attributes)
            if attributes is None:
                continue
            self.add_selector(selector_type, selector, attributes)

    def add_selector(self, selector_type: Type, name: str, attributes):
        if selector_type == self.Type.Universal:
            if self.universal_selector is None:
                self.universal_selector = attributes
            else:
                self.universal_selector.add(attributes)
        elif selector_type == self.Type.Id:
            selector_attributes = self.id_selectors.get(name)
            if selector_attributes:
                selector_attributes.add(attributes)
            else:
                selector_attributes = attributes
            self.id_selectors[name] = selector_attributes
        elif selector_type == self.Type.Class:
            selector_attributes = self.class_selectors.get(name)
            if selector_attributes:
                selector_attributes.add(attributes)
            else:
                selector_attributes = attributes
            self.class_selectors[name] = selector_attributes
        elif selector_type == self.Type.Element:
            selector_attributes = self.selectors.get(name)
            if selector_attributes:
                selector_attributes.add(attributes)
            else:
                selector_attributes = attributes
            self.selectors[name] = selector_attributes
        else:
            pass

    def effective_selector(self, selector: Selector):
        none_attributes = Attributes()
        attributes = Attributes()
        attributes += self.universal_selector
        attributes += self.selectors.get(selector.element_name, none_attributes)
        for name in selector.element_classes:
            attributes += self.class_selectors.get(name, none_attributes)
        attributes += self.id_selectors.get(name, none_attributes)
        return attributes

    def __str__(self):
        return (
            f"selectors: {self.selectors}\n"
            f"id_selectors: {self.id_selectors}\n"
            f"class_selectors: {self.class_selectors}\n"
            f"universal_selector: {self.universal_selector}\n"
        )


class State(IntEnum):
    selector = (0,)
    open_sect = (1,)
    property = (2,)
    value = (3,)
    colon = 4
    semi_colon = (5,)
    comment = 6


class StringHelper:
    @staticmethod
    def multisplit(text: str, separators: str):
        result = []
        start_idx = 0
        idx = 0
        end = len(text)
        while idx < end:
            if text[idx] in separators:
                # '  a, b'
                # idx = 0, last_idx = 0
                if start_idx != idx:
                    # don't create empty zero len words
                    result.append(text[start_idx:idx])
                start_idx = idx + 1
            idx += 1
        if start_idx != idx:
            # last word
            result.append(text[start_idx:idx])
        return result

    @staticmethod
    def split_trim(text: str, separator):
        result = []
        for token in text.split(separator):
            token = token.strip()
            if token != "":
                result.append(token)
        return result


class CssParser:
    # TODO: properly handle nested { {
    # https://www.w3.org/TR/css-syntax-3/#parsing-overview

    @staticmethod
    def parse(file_name: str, selectors: Selectors) -> Selectors:
        if selectors is None:
            selectors = Selectors()
        with open(file_name, "r") as f:
            last_state = State.selector
            state = State.selector
            selector = None
            prop = None
            value = None
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
                    if state == State.comment:
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
                                state = State.comment
                                idx += 2
                                continue

                    if c in non_printables:
                        c = " "

                    if state == State.selector:
                        if len(word) > 0:
                            if c == "{":
                                # '*{'
                                #   ^
                                state = State.open_sect
                                # ommit increment - we will hit the switch for {
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
                    elif state == State.open_sect:
                        # if c == ' ':
                        #
                        #    # skipping spaces
                        #    pass
                        if c == "{":
                            selector = word
                            word = ""
                            state = State.property
                            pass
                        else:
                            failed = Exception(f'{line_num}: state: {state} - got "{c}" - line: "{line}"')
                            break
                        idx += 1
                        continue
                    elif state == State.property:
                        if c == ":":
                            state = State.colon
                            continue
                        elif c == "}":
                            # reset word
                            word = ""
                            state = State.selector
                        # elif c == ' ':
                        #     # yes, i know that this will remove spaces
                        #     pass
                        else:
                            word += c
                        idx += 1
                        continue
                    elif state == State.colon:
                        if c == ":":
                            prop = word
                            word = ""
                            state = State.value
                        # elif c == ' ':
                        #    pass
                        else:
                            failed = Exception(f'{line_num}: state: {state} - got "{c}" - line: "{line}"')
                            break
                        idx += 1
                        continue
                    elif state == State.value:
                        # if c == ' ':
                        #    pass
                        if c == ";":
                            state = State.semi_colon
                            continue
                        else:
                            word += c
                        idx += 1
                        continue
                    elif state == State.semi_colon:
                        if c == ";":
                            value = word
                            word = ""
                            state = State.property
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
