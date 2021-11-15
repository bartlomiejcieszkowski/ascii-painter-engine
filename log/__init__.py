import abc
import time
import threading
import pathlib
import enum
from collections import deque


class LogLevel(enum.IntEnum):
    ERROR = 1
    WARNING = 2
    INFO = 3
    VERBOSE = 4

import sys
from pathlib import Path

__level = LogLevel.INFO
__log_file = sys.stdout
__log_file_base = None
__log_file_path = None
__log_idx = 0
__log_idx_max = 5
__log_file_size_max = 5 * 1024 * 1024


__log_file_size_check_n = 0
__log_file_size_check_every_nth = 100


def set_log_level(level: LogLevel):
    global __level
    __level = level


def get_log_level() -> LogLevel:
    return __level


def log_verbose() -> bool:
    return __level >= LogLevel.VERBOSE

def log_file_next():
    global __log_file
    global __log_file_path
    global __log_idx
    if __log_file is not sys.stdout:
        __log_idx = (__log_idx + 1) % __log_idx_max
    log_file(__log_file_base)


def log_file(file_path):
    global __log_file
    global __log_file_path
    global __log_file_base
    if file_path is None:
        __log_file = sys.stdout
    else:
        __log_file_base = file_path
        __log_file_path = Path(__log_file_base +  '.{}'.format(__log_idx))
        __log_file = __log_file_path.open('w')


def log_flush():
    __log_file.flush()


def log(fmt, *args):
    global __log_file_size_check_n
    __log_file_size_check_n += 1
    if __log_file_size_check_n % __log_file_size_check_every_nth == 0:
        if __log_file is not sys.stdout:
            if __log_file_size_max < __log_file_path.stat().st_size:
                log_file_next()

    print(time.strftime("[%H:%M:%S]", time.localtime())
          + "[{:<10.10}] ".format(threading.current_thread().name) + str(fmt), *args, file=__log_file)
    log_flush()

