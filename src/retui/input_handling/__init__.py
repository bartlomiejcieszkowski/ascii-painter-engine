import selectors
from collections import deque
from enum import Enum, Flag, IntEnum

from retui.base import TerminalEvent
from retui.input_handling.enums import VirtualKeyCodes
from retui.input_handling.windows import MOUSE_EVENT_RECORD


class MouseEvent(TerminalEvent):
    last_mask = 0xFFFFFFFF

    dwButtonState_to_Buttons = [[0, 0], [1, 2], [2, 1]]

    class Buttons(IntEnum):
        LMB = 0
        RMB = 2
        MIDDLE = 1
        WHEEL_UP = 64
        WHEEL_DOWN = 65

    class ControlKeys(Flag):
        LEFT_CTRL = 0x8

    def __init__(self, x, y, button: Buttons, pressed: bool, control_key_state, hover: bool):
        super().__init__()
        self.coordinates = (x, y)
        self.button = button
        self.pressed = pressed
        self.hover = hover
        # based on https://docs.microsoft.com/en-us/windows/console/mouse-event-record-str
        # but simplified - right ctrl => left ctrl
        self.control_key_state = control_key_state

    def __str__(self):
        return (
            f"MouseEvent x: {self.coordinates[0]} y: {self.coordinates[1]} button: {self.button} "
            f"pressed: {self.pressed} control_key: {self.control_key_state} hover: {self.hover}"
        )

    @classmethod
    def from_windows_event(cls, mouse_event_record: MOUSE_EVENT_RECORD):
        # on windows position is 0-based, top-left corner

        hover = False
        # zero indicates mouse button is pressed or released
        if mouse_event_record.dwEventFlags != 0:
            if mouse_event_record.dwEventFlags == 0x1:
                hover = True
            elif mouse_event_record.dwEventFlags == 0x4:
                # mouse wheel move, high word of dwButtonState is dir, positive up
                return cls(
                    mouse_event_record.dwMousePosition.X,
                    mouse_event_record.dwMousePosition.Y,
                    MouseEvent.Buttons(MouseEvent.Buttons.WHEEL_UP + ((mouse_event_record.dwButtonState >> 31) & 0x1)),
                    True,
                    None,
                    False,
                )
                # TODO: high word
            elif mouse_event_record.dwEventFlags == 0x8:
                # horizontal mouse wheel - NOT SUPPORTED
                return None
            elif mouse_event_record.dwEventFlags == 0x2:
                # double click - TODO: do we need this?
                return None

        ret_list = []

        # on Windows we get mask of pressed buttons
        # we can either pass mask around and worry about translating it outside
        # we will have two different handlers on windows and linux,
        # so we just translate it into serialized clicks
        changed_mask = mouse_event_record.dwButtonState ^ MouseEvent.last_mask
        if hover:
            changed_mask = mouse_event_record.dwButtonState

        if changed_mask == 0:
            return None

        MouseEvent.last_mask = mouse_event_record.dwButtonState

        for dwButtonState, button in MouseEvent.dwButtonState_to_Buttons:
            changed = changed_mask & (0x1 << dwButtonState)
            if changed:
                press = mouse_event_record.dwButtonState & (0x1 << dwButtonState) != 0

                event = cls(
                    mouse_event_record.dwMousePosition.X,
                    mouse_event_record.dwMousePosition.Y,
                    MouseEvent.Buttons(button),
                    press,
                    None,
                    hover,
                )
                ret_list.append(event)

        if len(ret_list) == 0:
            return None

        return ret_list

    @classmethod
    def from_sgr_csi(cls, button_hex: int, x: int, y: int, press: bool):
        # print(f"0x{button_hex:X}", file=sys.stderr)
        move_event = button_hex & 0x20
        if move_event:
            # OPT1: don't support move
            # return None
            # OPT2: support move like normal click
            button_hex = button_hex & (0xFFFFFFFF - 0x20)
            # FINAL: TODO: pass it as Move mouse event and let
            # button = None
            # 0x23 on simple move.. with M..
            # 0x20 on move with lmb
            # 0x22 on move with rmb
            # 0x21 on move with wheel
            if button_hex & 0xF == 0x3:
                return None

        # TODO: wheel_event = button_hex & 0x40
        ctrl_button = 0x8 if button_hex & 0x10 else 0x0

        # remove ctrl button
        button_hex = button_hex & (0xFFFFFFFF - 0x10)
        button = MouseEvent.Buttons(button_hex)
        # sgr - 1-based
        if y < 2:
            return None

        # 1-based - translate to 0-based
        return cls(x - 1, y - 1, button, press, ctrl_button, False)


class KeyEvent(TerminalEvent):
    def __init__(
        self,
        key_down: bool,
        repeat_count: int,
        vk_code: int,
        vs_code: int,
        char,
        wchar,
        control_key_state,
    ):
        super().__init__()
        self.key_down = key_down
        self.repeat_count = repeat_count
        self.vk_code = vk_code
        self.vs_code = vs_code
        self.char = char
        self.wchar = wchar
        self.control_key_state = control_key_state

    def __str__(self):
        return (
            f"KeyEvent: vk_code={self.vk_code} vs_code={self.vs_code} char='{self.char}' wchar='{self.wchar}' "
            f"repeat={self.repeat_count} ctrl=0x{self.control_key_state:X} key_down={self.key_down} "
        )


class InputInterpreter:
    # linux
    # lmb 0, rmb 2, middle 1, wheel up 64 + 0, wheel down 64 + 1

    class State(Enum):
        DEFAULT = 0
        ESCAPE = 1
        CSI_BYTES = 2

    # this class should
    # receive data
    # and parse it accordingly
    # if it is ESC then start parsing it as ansi escape code
    # and emit event once we parse whole sequence
    # otherwise pass it to... input handler?

    # better yet:
    # this class should provide read method, and wrap the input provided

    def __init__(self, readable_input):
        self.input = readable_input
        self.state = self.State.DEFAULT
        self.input_raw = []
        self.ansi_escape_sequence = []
        self.payload = deque()
        self.last_button_state = [0, 0, 0]
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.input, selectors.EVENT_READ)
        self.selector_timeout_s = 1.0
        self.read_count = 64

    # 9 Normal \x1B[ CbCxCy M , value + 32 -> ! is 1 - max 223 (255 - 32)
    # 1006 SGR  \x1B[<Pb;Px;Py[Mm] M - press m - release
    # 1015 URXVT \x1B[Pb;Px;Py M - not recommended, can be mistaken for DL
    # 1016 SGR-Pixel x,y are pixels instead of cells
    # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html

    def parse(self):
        # ConsoleView.log(f'parse: {self.ansi_escape_sequence}')
        # should append to self.event_list
        length = len(self.ansi_escape_sequence)

        if length < 3:
            # minimal sequence is ESC [ (byte in range 0x40-0x7e)
            self.payload.append(str(self.ansi_escape_sequence))
            return

        # we can safely skip first 2 bytes
        if self.ansi_escape_sequence[2] == "<":
            # for mouse last byte will be m or M character
            if self.ansi_escape_sequence[-1] not in ("m", "M"):
                self.payload.append(str(self.ansi_escape_sequence))
                return
            # SGR
            idx = 0
            values = [0, 0, 0]
            temp_word = ""
            press = False
            for i in range(3, length + 1):
                ch = self.ansi_escape_sequence[i]
                if idx < 2:
                    if ch == ";":
                        values[idx] = int(temp_word, 10)
                        idx += 1
                        temp_word = ""
                        continue
                elif ch in ("m", "M"):
                    values[idx] = int(temp_word, 10)
                    if ch == "M":
                        press = True
                    break
                temp_word += ch
            # msft
            # lmb 0x1 rmb 0x2, lmb2 0x4 lmb3 0x8 lmb4 0x10
            # linux
            # lmb 0, rmb 2, middle 1, wheel up 64 + 0, wheel down 64 + 1
            # move 32 + key
            # shift   4
            # meta    8
            # control 16
            # print(f"0X{values[0]:X} 0X{values[1]:X} 0x{values[2]:X}, press={press}", file=sys.stderr)
            mouse_event = MouseEvent.from_sgr_csi(values[0], values[1], values[2], press)
            if mouse_event:
                self.payload.append(mouse_event)
            return

        # normal - TODO
        # self.payload.extend(str(self.ansi_escape_sequence))
        len_aes = len(self.ansi_escape_sequence)
        if len_aes == 3:
            third_char = ord(self.ansi_escape_sequence[2])
            vk_code = 0
            char = b"\x00"
            wchar = ""
            if third_char == 65:
                # A - Cursor Up
                vk_code = VirtualKeyCodes.VK_UP
            elif third_char == 66:
                # B - Cursor Down
                vk_code = VirtualKeyCodes.VK_DOWN
            elif third_char == 67:
                # C - Cursor Right
                vk_code = VirtualKeyCodes.VK_RIGHT
            elif third_char == 68:
                # D - Cursor Left
                vk_code = VirtualKeyCodes.VK_LEFT
            else:
                self.payload.append(str(self.input_raw))
                return
            self.payload.append(
                KeyEvent(
                    key_down=True,
                    repeat_count=1,
                    vk_code=vk_code,
                    vs_code=vk_code,
                    char=char,
                    wchar=wchar,
                    control_key_state=0,
                )
            )
        elif len_aes == 4:
            # 1 ~ Home
            # 2 ~ Insert
            # 3 ~ Delete
            # 4 ~ End
            # 5 ~ PageUp
            # 6 ~ PageDown
            pass
        elif len_aes == 5:
            # 1 1 ~ F1
            # ....
            # 1 5 ~ F5
            # 1 7 ~ F6
            # 1 8 ~ F7
            # 1 9 ~ F8
            # 2 0 ~ F9
            # 2 1 ~ F10
            # 2 3 ~ F11
            # 2 3 ~ F12
            pass

        self.payload.append(str(self.input_raw))
        return

    def parse_keyboard(self):
        if len(self.input_raw) > 1:
            # skip for now
            self.payload.append(str(self.input_raw))
            return
        wchar = self.input_raw[0]
        if wchar.isprintable() is False:
            # skip for now
            self.payload.append(str(self.input_raw))
            return
        # https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
        # key a is for both upper and lower case
        # vk_code = wchar.lower()
        self.payload.append(
            KeyEvent(
                key_down=True,
                repeat_count=1,
                vk_code=VirtualKeyCodes.from_ascii(ord(wchar)),
                vs_code=ord(wchar),
                char=wchar.encode(),
                wchar=wchar,
                control_key_state=0,
            )
        )
        return

    def read(self, count: int = 1):
        # ESC [ followed by any number in range 0x30-0x3f, then any between 0x20-0x2f, and final byte 0x40-0x7e
        # TODO: this should be limited so if one pastes long, long text this wont create arbitrary size buffer
        ready = self.selector.select(self.selector_timeout_s)
        if not ready:
            return None

        ch = self.input.read(self.read_count)
        while ch is not None and len(ch) > 0:
            self.input_raw.extend(ch)
            ch = self.input.read(self.read_count)

        if len(self.input_raw) > 0:
            for i in range(0, len(self.input_raw)):
                ch = self.input_raw[i]
                if self.state != self.State.DEFAULT:
                    ord_ch = ord(ch)
                    if 0x20 <= ord_ch <= 0x7F:
                        if self.state == self.State.ESCAPE:
                            if ch == "[":
                                self.ansi_escape_sequence.append(ch)
                                self.state = self.State.CSI_BYTES
                                continue
                        elif self.state == self.State.CSI_BYTES:
                            if 0x30 <= ord_ch <= 0x3F:
                                self.ansi_escape_sequence.append(ch)
                                continue
                            elif 0x40 <= ord_ch <= 0x7E:
                                # implicit IntermediateBytes
                                self.ansi_escape_sequence.append(ch)
                                self.parse()
                                self.state = self.State.DEFAULT
                                continue
                    # parse what we had collected so far, since we failed check above
                    self.parse()
                    self.state = self.State.DEFAULT
                    # intentionally fall through to regular parse
                # check if escape code
                if ch == "\x1B":
                    self.ansi_escape_sequence.clear()
                    self.ansi_escape_sequence.append(ch)
                    self.state = self.State.ESCAPE
                    continue

                # pass input to handler
                # here goes key, but what about ctrl, shift etc.? these are regular AsciiChar equivalents
                # no key up, only key down, is there \x sequence to enable extended? should be imho
                self.parse_keyboard()
                pass
            # DEBUG - don't do "".join, as the sequences are not printable
            # self.payload.append(str(self.input_raw))
            self.input_raw.clear()

            if len(self.payload) > 0:
                payload = self.payload
                self.payload = deque()
                return payload

        return None
