#!/usr/bin/env python3

import ascii_painter_engine as ape


def test() -> int:
    cv = ape.ConsoleView()
    if cv.color_mode() is False:
        print('Abort')
        return -1

    print("\x1B[34m" + 'TEST 8bit ANSII Codes' + "\x1B[0m")
    ape.Test.ColorLine(0, 8, use_color=True, width=2)
    ape.Test.ColorLine(8, 16, use_color=True, width=2)
    for red in range(0, 6):
        start = 16 + 6 * 6 * red
        end = start + 36
        ape.Test.ColorLine(start, end, use_color=True, width=3)

    ape.Test.ColorLine(232, 256, use_color=True, width=4)

    brush = ape.Brush()

    brush.SetBgColor(4)
    brush.SetFgColor(14)
    print("TEST", end='')
    brush.Reset()
    print()

    brush.print("TEST", fgcolor=14, bgcolor=4, end='\n')


if __name__ == '__main__':
    test()
