#!/usr/bin/env python3
import json
import subprocess  # nosec B404

from retui import App, helper

PROCESS_WRAP = None


class FileWrapper:
    def __init__(self):
        from tempfile import TemporaryFile

        self.file = TemporaryFile()
        self.rp = 0

    def get_file(self, rewind=True):
        if rewind:
            self.file.seek(0)
        return self.file

    def save_read_ptr(self):
        self.rp = self.file.tell()

    def read(self, n: int = -1):
        self.file.seek(self.rp)
        ret = self.file.read()
        if ret:
            ret = ret.decode("utf-8")
        self.save_read_ptr()
        return ret


class ProcessWrap:
    def __init__(self, args, stdout_widget, stderr_widget):
        self.args = args
        self.stdout_widget = stdout_widget
        self.stderr_widget = stderr_widget
        self.proc = None
        self.stdout_wrapper = FileWrapper()
        self.stderr_wrapper = FileWrapper()

    def run(self):
        print("HERE")
        # kwargs = {"args": self.args, "shell": True, "encoding": "utf-8", "text": True, "capture_output": True}
        # threading.Thread(subprocess.c)

        # self.proc = subprocess.run(
        self.proc = subprocess.Popen(
            args=self.args,
            shell=True,
            stdout=self.stdout_wrapper.get_file(rewind=True),
            stderr=self.stderr_wrapper.get_file(rewind=True),
            # stdin=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            universal_newlines=True,
            # capture_output=True,
        )
        pid = self.proc.pid
        print(f"ProcessWrap.run: {type(self.proc)} - {self.proc} - {pid}")
        out, err = self.proc.communicate()
        # stdout = self.stdout_wrapper.read()

        # print(f"stdout: {stdout}")
        # print(f"out: {out}\nerr: {err}")
        # raise Exception("DUPA")
        self.stdout_widget.write(self.stdout_wrapper.read())
        self.stderr_widget.write(self.stderr_wrapper.read())
        self.proc.terminate()
        print("THERE")


def sample_app_wrap(app: App):
    global PROCESS_WRAP
    process_list = [["git", "log", "--oneline"], ["dir"], ["python"]]
    PROCESS_WRAP = ProcessWrap(
        process_list[0], stdout_widget=app.get_widget_by_id("stdout"), stderr_widget=app.get_widget_by_id("stderr")
    )

    PROCESS_WRAP.run()
    # raise Exception("STOP HERE")


def test(handle_sigint=True, demo_time_s=None, title=None):
    print(title)
    working_directory = "tests/functional"
    apps = [("json/sample_app_wrap.json", sample_app_wrap)]

    for file, fun in apps:
        filename = working_directory + "/" + file
        with open(working_directory + "/" + file, "r") as f:
            data = json.load(f)
            for widget in data["widgets"]:
                print(widget)
        app = helper.app_from_json(filename, globals(), app_dict={"post": sample_app_wrap})
        app.handle_sigint = handle_sigint
        app.demo_mode(demo_time_s)
        app.run()
