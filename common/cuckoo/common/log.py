# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import sys
from copy import copy
from logging import handlers
from os import getenv
from queue import Queue

class ColorText:
    @staticmethod
    def color(text, color_code):
        """Colorize text.
        @param text: text.
        @param color_code: color.
        @return: colorized text.
        """
        # $TERM under Windows:
        # cmd.exe -> "" (what would you expect..?)
        # cygwin -> "cygwin" (should support colors, but doesn't work somehow)
        # mintty -> "xterm" (supports colors)
        # Win10 WSL -> "xterm-256color"

        if not ColorText.terminal_supported():
            return text

        return f"\x1b[{color_code}m{text}\x1b[0m"

    @staticmethod
    def terminal_supported():
        terms = ("xterm", "xterm-256color")
        if sys.platform == "win32" and getenv("TERM") not in terms:
            return False
        return True

    @staticmethod
    def black(text):
        return ColorText.color(text, 30)

    @staticmethod
    def red(text):
        return ColorText.color(text, 31)

    @staticmethod
    def green(text):
        return ColorText.color(text, 32)

    @staticmethod
    def yellow(text):
        return ColorText.color(text, 33)

    @staticmethod
    def blue(text):
        return ColorText.color(text, 34)

    @staticmethod
    def magenta(text):
        return ColorText.color(text, 35)

    @staticmethod
    def cyan(text):
        return ColorText.color(text, 36)

    @staticmethod
    def white(text):
        return ColorText.color(text, 37)

    @staticmethod
    def bold(text):
        return ColorText.color(text, 1)


def print_info(msg):
    print(ColorText.green(msg))

def print_warning(msg):
    print(ColorText.yellow(msg))

def print_error(msg):
    print(ColorText.red(msg))

def exit_error(msg):
    sys.exit(ColorText.red(msg))


_level = logging.INFO

def set_level(level):
    global _level
    _level = level
    logging.getLogger().setLevel(_level)

def add_rootlogger_handler(handler):
    handler.setLevel(_level)
    logging.getLogger().addHandler(handler)

# Infinite log queue size
_log_queue = Queue(maxsize=0)
_queue_handler = handlers.QueueHandler(_log_queue)

# Queue listener must be created and started once during startup
_queue_listener = None

def start_queue_listener(*queumsg_handlers):
    global _queue_listener

    for handler in queumsg_handlers:
        handler.setLevel(_level)

    # All queuemsg_handlers are called when a message is handled by the
    # queue_listener.
    _queue_listener = handlers.QueueListener(_log_queue, *queumsg_handlers)
    _queue_listener.start()

    # All log messages should flow to the queue by default if the queue
    # listener is started.
    _queue_handler.setLevel(_level)
    add_rootlogger_handler(_queue_handler)

def stop_queue_listener():
    # Stop the queue listener to ensure queued log messages are logged
    # to their handler before the process exits.
    if not _queue_listener:
        return

    _queue_listener.stop()
    for handler in _queue_listener.handlers:
        handler.close()

_KV_KEY = "_cuckoo_kv"

def _format_cuckoo_kvs(record, key_color_func=None):
    key_vals = record.__dict__.get(_KV_KEY)
    if not key_vals:
        return record

    if not key_color_func:
        kvs = [f'{key}={val}' for key, val in key_vals.items()]
    else:
        # If a color was specified, make the each key that color
        kvs = [
            f'{key_color_func(key)}={val}'
            for key, val in key_vals.items()
        ]

    # Build the message. Add a dot after the msg end if it does not have one.
    # This is to make it clear where the msg ends and the key values begin.
    record.msg = f"{record.msg}" \
                 f"{'.' if not record.msg.endswith('.') else ''} " \
                 f"{' '.join(kvs)}"

    return record

class KeyValueLogFormatter(logging.Formatter):

    def format(self, record):
        key_vals = record.__dict__.get(_KV_KEY)
        if not key_vals:
            return super().format(record)

        return super().format(_format_cuckoo_kvs(record))

class ConsoleFormatter(logging.Formatter):

    def format(self, record):
        # Create a copy of the record and format that. The copy is required
        # as the LogRecord instance is shared among all log handlers.
        console_copy = copy(record)

        bold_lvlname = ColorText.bold(record.levelname)
        if record.levelno == logging.INFO:
            console_copy.levelname = ColorText.green(bold_lvlname)
        elif record.levelno == logging.WARNING:
            console_copy.levelname = ColorText.yellow(bold_lvlname)
        elif record.levelno in (logging.ERROR, logging.CRITICAL):
            console_copy.levelname = ColorText.red(bold_lvlname)
            console_copy.name = ColorText.red(record.name)
            console_copy.msg = ColorText.red(record.msg)
        else:
            console_copy.levelname = ColorText.white(bold_lvlname)

        return super().format(
            _format_cuckoo_kvs(console_copy, ColorText.magenta)
        )

class CuckooLogger:

    def __init__(self, logger):
        self._logger = logger

    def _log_msg(self, level, msg, extra_kvs):
        self._logger.log(level, msg, extra={_KV_KEY: extra_kvs})

    def _log_exception(self, msg, extra_kvs):
        self._logger.exception(msg, extra={_KV_KEY: extra_kvs})

    def debug(self, msg, **kwargs):
        self._log_msg(logging.DEBUG, msg, kwargs)

    def info(self, msg, **kwargs):
        self._log_msg(logging.INFO, msg, kwargs)

    def warning(self, msg, **kwargs):
        self._log_msg(logging.WARNING, msg, kwargs)

    def error(self, msg, **kwargs):
        self._log_msg(logging.ERROR, msg, kwargs)

    def exception(self, msg, **kwargs):
        self._log_exception(msg, kwargs)

    def fatal_error(self, msg, includetrace=True, **kwargs):
        msg = f"Exited on error: {msg}"
        if includetrace:
            self._log_exception(msg, kwargs)
        else:
            self._log_msg(logging.ERROR, msg, kwargs)
        sys.exit(1)


class CuckooGlobalLogger(CuckooLogger):

    def __init__(self, name):
        super().__init__(logging.getLogger(name))
