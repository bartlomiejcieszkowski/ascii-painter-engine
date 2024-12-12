from pathlib import Path

from retui.theme import CssParser


def test(handle_sigint=True, demo_time_s=None, title=None, debug=False) -> int:
    print(title)
    working_directory = Path(__file__).parent
    files = [
        "css_parser/long_one_line_wykop_pl.css",
    ]

    for file in files:
        selectors = CssParser.parse(working_directory / file, None)
        print("----------------------------------------------------")
        print(selectors)

    return 0
