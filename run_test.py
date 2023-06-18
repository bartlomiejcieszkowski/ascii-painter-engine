#!/usr/bin/env python3

import argparse
import importlib
import os
import os.path
import pkgutil
import sys

import logger
import tests

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
    if args.all:
        for idx in range(0, len(tests_list)):
            title = f"Test {idx+1}/{len(tests_list)} - {tests_list[idx]}"
            diagnostics_start()
            test_run(tests_list[idx], demo_time_s, title)
            diagnostics_end()

    else:
        title = f"Test {args.test}"
        diagnostics_start()
        test_run(args.test, demo_time_s, title)
        diagnostics_end()
    sys.exit(0)


if __name__ == "__main__":
    main()
