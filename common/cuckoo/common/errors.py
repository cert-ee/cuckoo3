# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from traceback import format_exc

from .strictcontainer import Errors

class ErrorTracker:

    def __init__(self):
        self.errors = []
        self.fatal_errs = []

    def add_error(self, error, caller_instance=None):
        if caller_instance:
            self.errors.append(
                f"{caller_instance.__class__.__name__}: {error!s}"
            )
        else:
            self.errors.append(str(error))

    def _add_fatal_error(self, error, exception=False):
        self.fatal_errs.append({
            "error": str(error),
            "traceback": format_exc() if exception else ""
        })

    def fatal_error(self, error):
        self._add_fatal_error(error, exception=False)

    def fatal_exception(self, error):
        self._add_fatal_error(error, exception=True)

    def has_errors(self):
        return len(self.errors) > 0 or self.has_fatal()

    def has_fatal(self):
        return len(self.fatal_errs) > 0

    def to_dict(self):
        return {
            "errors": self.errors,
            "fatal": self.fatal_errs
        }

    def to_container(self):
        return Errors(**self.to_dict())

    def to_file(self, filepath):
        Errors(**self.to_dict()).to_file(filepath)
