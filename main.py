class ConsoleBuffer:
    def __init__(self):
        pass


import ctypes
import ctypes.wintypes
import msvcrt
import sys


class WindowsConsole:
    def __init__(self):
        self.kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        self.setConsoleModeProto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD
        )
        self.setConsoleModeParams = (1, "hConsoleHandle", 0), (1, "dwMode", 0)
        self.setConsoleMode = self.setConsoleModeProto(('SetConsoleMode', self.kernel32), self.setConsoleModeParams)

        self.getConsoleModeProto = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPDWORD
        )
        self.getConsoleModeParams = (1, "hConsoleHandle", 0), (1, "lpMode")
        self.getConsoleMode = self.getConsoleModeProto(('GetConsoleMode', self.kernel32), self.setConsoleModeParams)
        self.consoleHandleOut = msvcrt.get_osfhandle(sys.stdout.fileno())
        self.consoleHandleIn = msvcrt.get_osfhandle(sys.stdin.fileno())

    def GetConsoleModeOut(self) -> int:
        dwMode = ctypes.wintypes.DWORD(0)
        lpMode = ctypes.wintypes.LPDWORD(dwMode)
        self.getConsoleMode(self.consoleHandleOut, lpMode)

        print(f' dwMode: {hex(dwMode.value)}')
        return dwMode.value

    def SetConsoleModeOut(self, mode):
        dwMode = ctypes.wintypes.DWORD(mode)
        self.setConsoleMode(self.consoleHandleOut, dwMode)
        return

    def EnableVT(self) -> bool:
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4
        consoleMode = self.GetConsoleModeOut()
        if consoleMode & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            return True

        consoleMode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        self.SetConsoleModeOut(consoleMode)
        consoleMode = self.GetConsoleModeOut()
        return (consoleMode & ENABLE_VIRTUAL_TERMINAL_PROCESSING) != 0


class Test:
    @staticmethod
    def ColorLine(start, end, text='  ', use_color=False, width=2):
        for color in range(start, end):
            print(f'\x1B[48;5;{color}m{("{:"+ str(width) + "}").format(color) if use_color else text}', end='')
        print('\x1B[0m')

    @staticmethod
    def ColorLine24bit(start,end,step=0):
        for color in range(start, end, step):
            print(f'\x1B[48;2;{color};{color};{color}mXD', end='')
        print('\x1B[0m')



def test():
    wc = WindowsConsole()
    success = wc.EnableVT()
    print(f'EnableVT? {success}')
    if not success:
        print('Abort')
        return
    print("\x1B[34m" + 'TEST 8bit ANSII Codes' + "\x1B[0m")
    Test.ColorLine(0, 8, use_color=True, width=2)
    Test.ColorLine(8, 16, use_color=True, width=2)
    for red in range(0, 6):
        start = 16 + 6 * 6 * red
        end = start + 36
        Test.ColorLine(start, end, use_color=True, width=3)

    Test.ColorLine(232, 256, use_color=True, width=4)


if __name__ == '__main__':
    test()
