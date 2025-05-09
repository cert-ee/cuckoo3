# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from threading import Lock, RLock

from cuckoo.common.log import CuckooGlobalLogger

from .errors import RooterError

log = CuckooGlobalLogger("rooter.undoable")


class Undoable:
    """Helper that wraps around a starting method and stopping method.
    These can be stored and their starting method effect 'undone'."""

    def __init__(
        self, apply_func=None, apply_args=None, undo_func=None, undo_args=None
    ):
        if apply_args is not None and not isinstance(apply_args, (tuple, list)):
            apply_args = (apply_args,)

        if apply_func:
            log.debug("Applying change", apply_func=apply_func, apply_args=apply_args)
            apply_func(*apply_args)

        if undo_args is not None and not isinstance(undo_args, (tuple, list)):
            undo_args = (undo_args,)

        self._tracked_by = set()
        self.undo_func = undo_func
        self.undo_args = undo_args or ()
        self._undo_lock = Lock()
        self._undo_used = False
        self._undone = False

    def add_tracker(self, undoable_tracker):
        self._tracked_by.add(undoable_tracker)

    def undo(self):
        if self._undo_used or not self.undo_func:
            return

        with self._undo_lock:
            self._undo_used = True
            for tracker in self._tracked_by:
                tracker.remove(self)

        log.debug("Undoing change", undo_func=self.undo_func, args=self.undo_args)
        self.undo_func(*self.undo_args)
        self._undone = True


class UndoableTracker:
    def __init__(self):
        self._lock = RLock()
        self._undoables = []

    def append(self, undoable):
        with self._lock:
            self._undoables.append(undoable)
            undoable.add_tracker(self)

    def remove(self, undoable):
        with self._lock:
            self._undoables.remove(undoable)

    def undo_all(self):
        with self._lock:
            # Undo actions in LIFO order. First remove rules, then delete table
            # etc
            for undoable in reversed(self._undoables[:]):
                try:
                    undoable.undo()
                except RooterError as e:
                    log.error("Failed to run undo command", error=e)
