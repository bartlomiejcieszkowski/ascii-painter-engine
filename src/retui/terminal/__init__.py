from retui.utils import is_windows


class TerminalBuffer:
    _cached = None

    def __init__(self, width: int, height: int, symbol: str, debug: bool):
        self.width = width
        self.height = height
        self.symbol = symbol
        self.debug = debug
        self.buffer = []
        if self.debug:
            # print numbered border
            line = ""
            for col in range(width):
                line += str(col % 10)
            self.buffer.append(line)
            middle = symbol * (width - 2)
            for row in range(1, height - 1):
                self.buffer.append(str(row % 10) + middle + str(row % 10))
            self.buffer.append(line)
        else:
            line = symbol * width
            for i in range(height):
                self.buffer.append(line)

    def same(self, width: int, height: int, symbol: str, debug: bool) -> bool:
        return self.width == width and self.height == height and self.symbol == symbol and self.debug == debug

    @staticmethod
    def get_buffer(width, height, symbol=" ", debug=True):
        if TerminalBuffer._cached and TerminalBuffer._cached.same(width, height, symbol, debug):
            return TerminalBuffer._cached.buffer

        TerminalBuffer._cached = TerminalBuffer(width, height, symbol, debug)
        return TerminalBuffer._cached.buffer


if is_windows():
    from retui.terminal.windows import WindowsTerminal

    def get_terminal(app) -> WindowsTerminal:
        return WindowsTerminal(app)

else:
    from retui.terminal.linux import LinuxTerminal

    def get_terminal(app) -> LinuxTerminal:
        return LinuxTerminal(app)
