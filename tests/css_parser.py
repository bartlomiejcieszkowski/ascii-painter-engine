#!/usr/bin/env python3
import ascii_painter_engine as ape
from ascii_painter_engine.theme import CssParser


def test(handle_sigint=True, demo_time_s=None):
    #app = ape.App(log=ape.log.log)

    working_directory = 'tests'
    files = [
        'css_parser/main.css'
    ]

    for file in files:
        selectors = CssParser.parse(working_directory + '/' + file, None)

    #app.handle_sigint = handle_sigint
    #app.demo_mode(demo_time_s)

    #app.run()