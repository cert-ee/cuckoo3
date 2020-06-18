# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import traceback
import signal

from threading import Lock

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
            print(f"Error while shutting down: {e}")
            traceback.print_exc()

def _wrap_call_registered_shutdowns(sig, frame):
    call_registered_shutdowns()

signal.signal(signal.SIGTERM, _wrap_call_registered_shutdowns)
signal.signal(signal.SIGINT, _wrap_call_registered_shutdowns)
