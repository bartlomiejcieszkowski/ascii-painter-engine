#!/usr/bin/env python3
import time

import ascii_painter_engine as ape


def test(handle_sigint=True, demo_time_s=None) -> int:
    cv = ape.App()
    if cv.color_mode() is False:
        print("Abort")
        return -1

    print("\x1B[34m" + "TEST 8bit ANSII Codes" + "\x1B[0m")
    ape.Test.ColorLine(0, 8, use_color=True, width=2)
    ape.Test.ColorLine(8, 16, use_color=True, width=2)
    for red in range(0, 6):
        start = 16 + 6 * 6 * red
        end = start + 36
        ape.Test.ColorLine(start, end, use_color=True, width=3)

    ape.Test.ColorLine(232, 256, use_color=True, width=4)

    brush = ape.Brush()

    test_color = ape.ConsoleColor(ape.Color(14, ape.ColorBits.Bit8), ape.Color(4, ape.ColorBits.Bit8))

    brush.SetBgColor(test_color.bgcolor)
    brush.SetFgColor(test_color.fgcolor)
    print("TEST", end="")
    brush.Reset()
    print()

    brush.print("TEST2", color=test_color, end="\n")
    if demo_time_s:
        time.sleep(demo_time_s)


if __name__ == "__main__":
    test()
