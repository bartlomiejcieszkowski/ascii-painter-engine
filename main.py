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


def test():
    wc = WindowsConsole()
    success = wc.EnableVT()
    print(f'EnableVT? {success}')
    if not success:
        print('Abort')
        return
    print("\x1B[34m" + 'TEST' + "\x1B[0m")

if __name__ == '__main__':
    test()
