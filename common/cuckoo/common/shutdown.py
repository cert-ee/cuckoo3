# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import signal
from threading import Lock, Thread

from .log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

_shutdown_methods = []
_teardown_lock = Lock()

_original_handlers = {
    signal.SIGINT: signal.getsignal(signal.SIGINT),
    signal.SIGTERM: signal.getsignal(signal.SIGINT)
}

_call_original = False
_currently_teardown = None

def set_call_original_handlers(call_original):
    """Set call original to false or true. Causes the shutdown handler
    to call any original Python signal handlers that might have existed.
    The original handlers are called after all registered shutdown handlers
    are called."""
    global _call_original
    _call_original = call_original

def register_shutdown(stop_method, order=10):
    """Add a method that stops or cleans up a component to the shutdown method
    list. All methods in this list a called when a SIGTERM or SIGINT is
    received, or when call_registered_shutdowns is called.

    :param order: The order of the calling of shutdown methods. Lower is
    earlier. Default is 10.
    """
    _shutdown_methods.append((stop_method, order))

def call_registered_shutdowns():
    if not _teardown_lock.acquire(blocking=False):
        return

    global _currently_teardown

    # Sort the shutdown methods to be ascending by the 'order' value.
    _shutdown_methods.sort(key=lambda method: method[1])
    for shutmethod, _ in _shutdown_methods:
        _currently_teardown = shutmethod
        try:
            shutmethod()
        except Exception as e:
            log.exception(
                "Error while calling shutdown method.",
                error=e, method=shutmethod
            )

def _wrap_call_registered_shutdowns(sig, frame):
    if _teardown_lock.locked():
        if _currently_teardown:
            print(f"Teardown is currently at: {_currently_teardown}")
        return

    # Delegate the actual handling of the signal to a new thread as IO
    # is not safe in a signal handler: https://bugs.python.org/issue24283
    sigth = Thread(target=call_registered_shutdowns)
    sigth.start()
    sigth.join()

    orig_handler = _original_handlers.get(sig)
    if _call_original and orig_handler:
        signal.signal(sig, orig_handler)
        os.kill(os.getpid(), sig)

signal.signal(signal.SIGTERM, _wrap_call_registered_shutdowns)
signal.signal(signal.SIGINT, _wrap_call_registered_shutdowns)
