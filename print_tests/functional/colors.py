#!/usr/bin/env python3
import time

import retui


def test(handle_sigint=True, demo_time_s=None, title=None) -> int:
    print(title)
    cv = retui.App()
    if cv.color_mode() is False:
        print("Abort")
        return -1

    print("\x1B[34m" + "TEST 8bit ANSII Codes" + "\x1B[0m")
    retui.Test.color_line(0, 8, use_color=True, width=2)
    retui.Test.color_line(8, 16, use_color=True, width=2)
    for red in range(0, 6):
        start = 16 + 6 * 6 * red
        end = start + 36
        retui.Test.color_line(start, end, use_color=True, width=3)

    retui.Test.color_line(232, 256, use_color=True, width=4)

    brush = retui.Brush()

    test_color = retui.TerminalColor(retui.Color(14, retui.ColorBits.Bit8), retui.Color(4, retui.ColorBits.Bit8))

    brush.set_foreground(test_color.background)
    brush.set_background(test_color.foreground)

    print("NICE TEXT", end="")
    print(brush.reset_color(), end="")
    print()

    brush.print("THIS ONE SHOULD BE INVERTED ONE ABOVE", color=test_color, end="\n")
    brush.print(test_color, color=test_color, end="\n")

    brush.print("This", "should", "have test color,", sep=" ", color=test_color)
    print(" and this should have default terminal color")
    if demo_time_s:
        time.sleep(demo_time_s)


if __name__ == "__main__":
    test()
