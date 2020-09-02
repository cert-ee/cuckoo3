# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import sys
from copy import copy
from logging import handlers
from os import getenv
from queue import Queue
from threading import Lock

from .storage import TaskPaths, AnalysisPaths

# Replace WARNING with WARN to keep log line shorter,
# aligned, and readable
logging.addLevelName(logging.WARNING, "WARN")

# Set the root level to DEBUG so we can easily use per-handler levels
logging.getLogger().setLevel(logging.DEBUG)

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

def add_rootlogger_handler(handler):
    handler.setLevel(_level)
    logging.getLogger().addHandler(handler)

def set_logger_level(loggername, level):
    logging.getLogger(loggername).setLevel(level)

def get_global_loglevel():
    return _level

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

        # Create a copy of the record and format that. The copy is required
        # as the LogRecord instance is shared among all log handlers.
        console_copy = copy(record)
        return super().format(_format_cuckoo_kvs(console_copy))

class ConsoleFormatter(logging.Formatter):

    EXTRA_CHAR_SIZE = len(ColorText.bold(ColorText.green("")))
    _COLOR_TERMINAL = ColorText.terminal_supported()

    def format(self, record):
        # Create a copy of the record and format that. The copy is required
        # as the LogRecord instance is shared among all log handlers.
        console_copy = copy(record)

        # If the terminal does not support ANSI colors, don't add them.
        if not self._COLOR_TERMINAL:
            return super().format(
                _format_cuckoo_kvs(console_copy, ColorText.magenta)
            )

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


_DEFAULT_LOG_FMT = "%(asctime)#ASCTIME_COLSIZE#s " \
                   "%(levelname)#LEVELNAME_COLSIZE#s " \
                   "[%(name)#NAME_COLSIZE#s]: %(message)s"

def _set_fmt_colsizes(asctime=None, levelname=None, name=None, align="left"):
    def _align_colsize(number):
        if align == "left" and number > 0:
            return str(-number)
        return str(number)

    fmt = _DEFAULT_LOG_FMT
    fmt = fmt.replace(
        "#ASCTIME_COLSIZE#", _align_colsize(asctime) if asctime else ""
    )
    fmt = fmt.replace(
        "#LEVELNAME_COLSIZE#", _align_colsize(levelname) if levelname else ""
    )
    fmt = fmt.replace("#NAME_COLSIZE#", _align_colsize(name) if name else "")
    return fmt



def _emit_write_once(stream, msg, terminator):
    stream.write(f"{msg}{terminator}")

class CuckooWatchedFileHandler(handlers.WatchedFileHandler):

    def emit(self, record):
        if self.stream is None:
            self.stream = self._open()
        else:
            self.reopenIfNeeded()

        stream = self.stream
        try:
            # Overwrite the default file handle logic of using 2 writes. One
            # for the message and another for the terminator.
            msg = self.format(record)
            _emit_write_once(stream, msg, self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

class MultiLogfileHandler(logging.Handler):

    def __init__(self, mapkey):
        super().__init__()

        # Map key is the key used to find an identifier in the _KV_KEY dict
        # given on a LogRecord. The value of the key is used to find a mapped
        # handler.
        self._mapkey = mapkey

        self._key_handler_map = {}
        self._map_lock = Lock()

    def map_handler(self, key, handler):
        with self._map_lock:
            if key in self._key_handler_map:
                raise KeyError(
                    f"Cannot add handler for key {key}. A mapped "
                    f"handler already exists. "
                    f"{self._key_handler_map[key]}"
                )

            self._key_handler_map[key] = handler

    def unmap_handler(self, key):
        with self._map_lock:
            handler = self._key_handler_map.pop(key, None)
            if handler is None:
                raise KeyError(f"No handler is mapped for key {key}")

            handler.close()

    def handle(self, record):
        map_key_val = record.__dict__.get(_KV_KEY, {}).get(self._mapkey)
        if not map_key_val:
            return
            # raise KeyError(
            #     f"Missing mapping key '{self._mapkey}'. Cannot lookup mapped "
            #     f"receiver for LogRecord: {record}"
            # )

        handler = self._key_handler_map.get(map_key_val)
        if not handler:
            return
            # raise KeyError(
            #     f"Cannot emit to unmapped receiver: {map_key_val} for "
            #     f"LogRecord: {record}"
            # )

        handler.handle(record)

    def close(self):
        super().close()
        with self._map_lock:
            for handler in list(self._key_handler_map.values()):
                handler.close()


# Default file and console handlers
file_handler = CuckooWatchedFileHandler
console_handler = logging.StreamHandler

# The default file and console formatters.
file_formatter = KeyValueLogFormatter
console_formatter = ConsoleFormatter

_DEFAULT_LEVELNAME_COLSIZE = 5

# Create the default fmt strings for log formatter used to file logs and logs
# to the console.
logtime_fmt_str = "%Y-%m-%d %H:%M:%S"

file_log_fmt_str = _set_fmt_colsizes(
    levelname=_DEFAULT_LEVELNAME_COLSIZE, align="left"
)

# Console logger use ConsoleFormatter as a default, which can add ANSI colors
# if the terminal supports its. This adds extra characters, these need to be
# taken into account when determining the column size.
if ColorText.terminal_supported():
    console_log_fmt_str = _set_fmt_colsizes(
        levelname=ConsoleFormatter.EXTRA_CHAR_SIZE +
                  _DEFAULT_LEVELNAME_COLSIZE, align="left"
    )
else:
    console_log_fmt_str = _set_fmt_colsizes(
        levelname=_DEFAULT_LEVELNAME_COLSIZE, align="left"
    )


class CuckooLogger:

    def __init__(self, logger):
        self._logger = logger

    def log_msg(self, level, msg, extra_kvs):
        self._logger.log(level, msg, extra={_KV_KEY: extra_kvs})

    def log_exception(self, m, extra_kvs):
        self._logger.exception(m, extra={_KV_KEY: extra_kvs})

    def debug(self, m, **kwargs):
        self.log_msg(logging.DEBUG, m, kwargs)

    def info(self, m, **kwargs):
        self.log_msg(logging.INFO, m, kwargs)

    def warning(self, m, **kwargs):
        self.log_msg(logging.WARNING, m, kwargs)

    def error(self, m, **kwargs):
        self.log_msg(logging.ERROR, m, kwargs)

    def exception(self, m, **kwargs):
        self.log_exception(m, kwargs)

    def fatal_error(self, m, includetrace=True, **kwargs):
        m = f"Exited on error: {m}"
        if includetrace:
            self.log_exception(m, kwargs)
        else:
            self.log_msg(logging.ERROR, m, kwargs)
        sys.exit(1)

    def cleanup(self):
        pass

    def close(self):
        pass


class CuckooGlobalLogger(CuckooLogger):

    def __init__(self, name):
        super().__init__(logging.getLogger(name))


# TODO make thread safe. It currently as it is only used once per process per
# task/analysis id.
class _KeyBasedFileLogger(CuckooLogger):
    """Adds a MultiLogfileHandler to the specified logger name if it has not
     yet been added. Adds a file_handler for the given key afterwards.

     All messages arriving at the MultiLogfileHandler with _MAP_KEY=self.key
     will be logged to the given file_handler.

     This logger must always be closed.
     """

    _MAP_KEY = ""

    _multi_handler = None
    _multi_handler_lock = Lock()

    def __init__(self, name, key):
        super().__init__(logging.getLogger(name))
        self.key = key

        self._filepath = self.make_logfile_path()
        self._logfile_handler = None

        self._init_multihandler()
        self._multihandler_to_logger(self._logger)
        self._add_to_multihandler()

    @classmethod
    def _init_multihandler(cls):
        with cls._multi_handler_lock:
            if cls._multi_handler:
                return

            cls._multi_handler = MultiLogfileHandler(
                cls._MAP_KEY
            )
            cls._multi_handler.setLevel(logging.DEBUG)

    @classmethod
    def _multihandler_to_logger(cls, logger):
        with cls._multi_handler_lock:
            if cls._multi_handler in logger.handlers:
                return

            logger.addHandler(cls._multi_handler)

    def make_logfile_path(self):
        """Must create path to a file to use for logging and return it."""
        raise NotImplementedError

    def _add_to_multihandler(self):
        # Use the module default file log handler and formatter
        logfile_handler = file_handler(self._filepath, mode="a")

        # The tasklog will always be debug for now. The debug messages
        # for tasks will not be written to the cuckoo.log or console if
        # the global level is higher than debug.
        logfile_handler.setLevel(logging.DEBUG)
        logfile_handler.setFormatter(
            file_formatter(file_log_fmt_str, logtime_fmt_str)
        )

        self._logfile_handler = logfile_handler
        self._multi_handler.map_handler(self.key, logfile_handler)

    def log_msg(self, level, m, extra_kvs):
        extra_kvs[self._MAP_KEY] = self.key
        super().log_msg(level, m, extra_kvs)

    def log_exception(self, m, extra_kvs):
        extra_kvs[self._MAP_KEY] = self.key
        super().log_exception(m, extra_kvs)

    def close(self):
        if self._logfile_handler:
            self._logfile_handler.close()
            self._multi_handler.unmap_handler(self.key)
            self._logfile_handler = None

    def __del__(self):
        self.close()

class TaskLogger(_KeyBasedFileLogger):

    _MAP_KEY = "task_id"

    def make_logfile_path(self):
        return TaskPaths.tasklog(self.key)

class AnalysisLogger(_KeyBasedFileLogger):

    _MAP_KEY = "analysis_id"

    def make_logfile_path(self):
        return AnalysisPaths.analysislog(self.key)
