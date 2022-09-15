from abc import ABC
from enum import IntEnum

from ascii_painter_engine import ConsoleColor, Color


class Selector:
    def __init__(self, element_name: str, element_id: str, element_classes: list[str]):
        self.element_name = element_name
        self.element_id = element_id
        self.element_classes = element_classes


class Attributes:
    def __init__(self):
        self.color = ConsoleColor(fgcolor=Color(None), bgcolor=Color(None))

    def __add__(self, other):
        if other.color.fgcolor is not None:
            self.color.fgcolor = other.color.fgcolor
        if other.color.bgcolor is not None:
            self.color.bgcolor = other.color.bgcolor


class Selectors(ABC):
    def __init__(self):
        # selectors are inspired by css
        # TODO: allow styling by css stylesheet, but with limited subset
        self.selectors = {}
        self.id_selectors = {}
        self.class_selectors = {}
        self.universal_selector = None

    def add_selector(self, name: str, attributes):
        if name == '*':
            self.universal_selector = attributes
        elif name.startswith('#'):
            self.id_selectors[name] = attributes
        elif name.startswith('.'):
            self.class_selectors[name] = attributes
        else:
            self.selectors[name] = attributes

    def effective_selector(self, selector: Selector):
        none_attributes = Attributes()
        attributes = Attributes()
        attributes += self.universal_selector
        attributes += self.selectors.get(selector.element_name, none_attributes)
        for name in selector.element_classes:
            attributes += self.class_selectors.get(name, none_attributes)
        attributes += self.id_selectors.get(name, none_attributes)
        return attributes


class State(IntEnum):
    selector = 0,
    open_sect = 1,
    property = 2,
    value = 3,
    colon = 4
    semi_colon = 5,
    comment = 6


class CssParser:
    @staticmethod
    def dummy_split(text: str, sep: str):
        if len(text) <= len(sep):
            return None
        new_words = []
        curr_idx = 0
        try:
            while True:
                idx = text.index(sep, curr_idx)
                if idx == curr_idx:
                    # eg. ":text" idx=0, "::text" idx=1
                    new_words.append(text[idx:(idx+len(sep))])
                else:
                    new_words.append(text[curr_idx:idx])
                    new_words.append(sep)
                curr_idx = idx + len(sep)
        except ValueError:
            if curr_idx == 0:
                return None
            if curr_idx < len(text):
                new_words.append(text[curr_idx:])
        return new_words

    @staticmethod
    def split_special(line: str):
        words = line.split()
        filtered_words = []
        restart = True
        while restart:
            restart = False
            new_words = []
            for word in words:
                if restart:
                    new_words.append(word)
                    continue

                for sep in ['{', '}', ':', ';', '/*', '*/']:
                    splitted = CssParser.dummy_split(word, sep)
                    if splitted is not None:
                        new_words.extend(splitted)
                        restart = True
                        break
                if restart:
                    continue

                new_words.append(word)
            words = new_words
        return words

    @staticmethod
    def parse(file_name: str, selectors: Selectors) -> Selectors:
        if selectors is None:
            selectors = Selectors()
        with open(file_name, 'r') as f:
            last_state = State.selector
            state = State.selector
            selector = None
            property = None
            value = None
            failed = None
            line_num = 0
            for line in f:
                line_num += 1
                words = CssParser.split_special(line)
                for word in words:
                    if state == State.comment:
                        # ignore till */
                        if word == '*/':
                            state = last_state
                    elif word == '/*':
                        last_state = state
                        state = State.comment
                    elif state == State.selector:
                        selector = word
                        # validate selector
                        state = State.open_sect
                    elif state == State.open_sect:
                        if word != '{':
                            failed = Exception(f'{line_num}: state: {state} - expected ' + '{' + f' - got "{word}" - line: "{line}"')
                            break
                        else:
                            state = State.property
                    elif state == State.property:
                        if word == '}':
                            state = State.selector
                        else:
                            property = word
                            state = State.colon
                    elif state == State.colon:
                        if word != ':':
                            failed = Exception(f'{line_num}: state: {state} - expected : - got "{word}" - line: "{line}"')
                            break
                        state = State.value
                    elif state == State.value:
                        value = word
                        state = State.semi_colon
                    elif state == State.semi_colon:
                        if word != ';':
                            failed = Exception(f'{line_num}: state: {state} - expected ; - got "{word}" - line: "{line}"')
                            break
                        else:
                            print(f'{selector} {{ {property}: {value}; }}')
                            # TODO: PARSE PROPERTY
                            state = State.property

                if failed:
                    break

            if failed:
                # cleanup goes here
                raise failed

        return selectors
