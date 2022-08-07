#!/usr/bin/env python3


import argparse
import os.path
import pkgutil
import signal
import subprocess

import tests
import importlib
import sys

import log

from multiprocessing import Process
import time
import os


def test_run(module_name, demo_time_s):
    print(module_name)
    sys.path.append(os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir, '..')))
    x = importlib.import_module(f'tests.{module_name}')
    log.log_file(f'{module_name}')
    x.test(demo_time_s=demo_time_s)


def main():
    tests_path = os.path.dirname(tests.__file__)
    tests_list = [name for _, name, _ in pkgutil.iter_modules([tests_path])]
    # print(tests_list)
    parser = argparse.ArgumentParser(description='Run tests.')
    parser.add_argument('--test', '-t', choices=tests_list, required=True)
    parser.add_argument('--auto', action='store_true', help='runs test and ends it')
    args = parser.parse_args()

    demo_time_s = None
    if args.auto:
        demo_time_s = 5
    test_run(args.test, demo_time_s)
    sys.exit(0)


if __name__ == '__main__':
    main()
