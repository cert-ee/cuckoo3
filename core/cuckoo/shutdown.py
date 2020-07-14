# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import signal
from threading import Lock, Thread

from cuckoo.common.log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

_shutdown_methods = []
_teardown_lock = Lock()

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

    # Sort the shutdown methods to be ascending by the 'order' value.
    _shutdown_methods.sort(key=lambda method: method[1])
    for shutmethod, _ in _shutdown_methods:
        try:
            shutmethod()
        except Exception as e:
            log.exception(
                "Error while calling shutdown method.",
                error=e, method=shutmethod
            )

def _wrap_call_registered_shutdowns(sig, frame):
    if _teardown_lock.locked():
        return

    # Delegate the actual handling of the signal to a new thread as IO
    # is not safe in a signal handler: https://bugs.python.org/issue24283
    Thread(target=call_registered_shutdowns).start()

signal.signal(signal.SIGTERM, _wrap_call_registered_shutdowns)
signal.signal(signal.SIGINT, _wrap_call_registered_shutdowns)
