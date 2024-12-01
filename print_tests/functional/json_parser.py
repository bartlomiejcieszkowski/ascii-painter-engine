#!/usr/bin/env python3
import json
from pathlib import Path

from retui import helper


def test(handle_sigint=True, demo_time_s=None, title=None):
    print(title)
    print(Path(__file__).parent)

    working_directory = Path(__file__).parent
    files = [
        "json/sample_app.json",
    ]

    for file in files:
        filename = working_directory / file
        with open(filename, "r", encoding="UTF-8") as f:
            data = json.load(f)
            for widget in data["widgets"]:
                print(widget)
        app = helper.app_from_json(filename, ctx_globals=globals())
        app.handle_sigint = handle_sigint
        app.demo_mode(demo_time_s)
        app.run()
