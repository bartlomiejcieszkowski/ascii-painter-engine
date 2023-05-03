#!/usr/bin/env python3
from ascii_painter_engine.theme import CssParser


def test(handle_sigint=True, demo_time_s=None):
    working_directory = "tests"
    files = [
        "css_parser/long_one_line_wykop_pl.css",
    ]

    for file in files:
        selectors = CssParser.parse(working_directory + "/" + file, None)
        print(selectors)
