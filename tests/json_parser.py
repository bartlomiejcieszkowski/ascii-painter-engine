#!/usr/bin/env python3
import json


def test(handle_sigint=True, demo_time_s=None, title=None):
    print(title)
    working_directory = "tests"
    files = [
        "json/sample_app.json",
    ]

    for file in files:
        with open(working_directory + "/" + file, "r") as f:
            data = json.load(f)
            for widget in data["widgets"]:
                print(widget)
