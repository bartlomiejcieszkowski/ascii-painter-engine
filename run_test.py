#!/usr/bin/env python3

import argparse
import importlib
import os
import os.path
import pkgutil
import sys

sys.path.append(os.path.abspath("./src/"))


import retui.logger as logger  # noqa: E402
import tests  # noqa: E402

DIAGNOSTICS = False
try:
    import gc

    import psutil

    DIAGNOSTICS = True
    DIAGNOSTICS_PID = os.getpid()
    DIAGNOSTICS_PROCESS = psutil.Process(DIAGNOSTICS_PID)
except ModuleNotFoundError:
    pass


def diagnostics_start():
    if DIAGNOSTICS:
        global DIAGNOSTICS_PROCESS
        gc.disable()
        gc.collect()
        global DIAGNOSTICS_MEMORY_INFO
        DIAGNOSTICS_MEMORY_INFO = DIAGNOSTICS_PROCESS.memory_info()


def diagnostics_end():
    if DIAGNOSTICS:
        global DIAGNOSTICS_PROCESS
        global DIAGNOSTICS_MEMORY_INFO
        memory_info = DIAGNOSTICS_PROCESS.memory_info()
        print(
            f"DIAGNOSTICS(rss({(memory_info.rss - DIAGNOSTICS_MEMORY_INFO.vms) // 1024}KiB), "
            f"vms({(memory_info.vms - DIAGNOSTICS_MEMORY_INFO.vms) // 1024}KiB)"
        )
        gc.collect()
        gc.enable()


def test_run(module_name, demo_time_s, title):
    print(module_name)
    sys.path.append(os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir, "..")))
    x = importlib.import_module(f"tests.{module_name}")
    logger.log_file(f"{module_name}")
    x.test(demo_time_s=demo_time_s, title=title)


def main():
    tests_path = os.path.dirname(tests.__file__)
    tests_list = [name for _, name, _ in pkgutil.iter_modules([tests_path])]
    # print(tests_list)
    parser = argparse.ArgumentParser(description="Run tests.")
    parser.add_argument("--auto", action="store_true", help="runs test and ends it")
    parser.add_argument("--auto-time", type=int, help="demo time", default=5)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test", "-t", choices=tests_list)
    group.add_argument("--all", action="store_true", help="runs ALL available tests")
    args = parser.parse_args()

    demo_time_s = None
    if args.auto:
        demo_time_s = args.auto_time

    test_status = []
    if args.all:
        status = []
        for idx in range(0, len(tests_list)):
            title = f"Test {idx+1}/{len(tests_list)} - {tests_list[idx]}"
            diagnostics_start()
            try:
                test_run(tests_list[idx], demo_time_s, title)
                test_status.append((0, tests_list[idx], None))
            except Exception as e:
                test_status.append((-1, tests_list[idx], e))
            diagnostics_end()
    else:
        title = f"Test {args.test}"
        diagnostics_start()
        try:
            test_run(args.test, demo_time_s, title)
            test_status.append((0, args.test, None))
        except Exception as e:
            test_status.append((-1, args.test, e))
        diagnostics_end()

    ret = 0
    i = 0
    for status, test_name, exception in test_status:
        i += 1
        name_state = "PASS" if status == 0 else "FAIL"
        print(f'[{name_state}] {i:3d}: "{test_name}" - exception? {exception} status: {status}')
        if status != 0:
            ret = -1

    sys.exit(ret)


if __name__ == "__main__":
    main()
