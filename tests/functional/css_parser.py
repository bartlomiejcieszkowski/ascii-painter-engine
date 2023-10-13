#!/usr/bin/env python3
from retui.theme import CssParser


def test(handle_sigint=True, demo_time_s=None, title=None):
    print(title)
    working_directory = "tests/functional"
    files = [
        "css_parser/main.css",
    ]

    for file in files:
        selectors = CssParser.parse(working_directory + "/" + file, None)
        print(selectors)
