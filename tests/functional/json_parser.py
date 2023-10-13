#!/usr/bin/env python3
import json

from retui import helper
from retui.logger import log


def test(handle_sigint=True, demo_time_s=None, title=None):
    print(title)
    working_directory = "tests/functional"
    files = [
        "json/sample_app.json",
    ]

    for file in files:
        filename = working_directory + "/" + file
        with open(working_directory + "/" + file, "r") as f:
            data = json.load(f)
            for widget in data["widgets"]:
                print(widget)
        app = helper.app_from_json(filename, ctx_globals=globals(), log_fun=log)
        app.handle_sigint = handle_sigint
        app.demo_mode(demo_time_s)
        app.run()
