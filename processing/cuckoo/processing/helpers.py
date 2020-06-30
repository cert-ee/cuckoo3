# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import traceback

from .errors import CancelProcessing

# class ErrorTracker:
#     """A tracker instance made for each processing phase of an analysis.
#     The instance should be passed to processing modules and lastly, the
#     reporting modules should write it to disk."""
#
#     OK = "OK"
#     FATAL = "fatal"
#
#     def __init__(self):
#         self.state = self.OK
#         self.errors = []
#         self.fatal_err = {}
#
#     def add_error(self, caller_instance, error):
#         self.errors.append(f"{caller_instance.__class__.__name__}: {error}")
#
#     def set_fatal_error(self, error, exception=False):
#         if self.fatal_err:
#             raise NotImplementedError(
#                 f"Fatal error cannot be overwritten. Content: {self.fatal_err}"
#             )
#
#         self.state = self.FATAL
#         self.fatal_err = {
#             "error": error,
#             "traceback": traceback.format_exc() if exception else ""
#         }
#
#     def fatal_error(self, error):
#         self.set_fatal_error(error, exception=False)
#         raise CancelProcessing(error)
#
#     def fatal_exception(self, error):
#         self.set_fatal_error(error, exception=True)
#         raise CancelProcessing(error)
#
#     def has_errors(self):
#         return len(self.errors) > 0 or len(self.fatal_err) > 0
#
#     def to_dict(self):
#         return {
#             "errors": self.errors,
#             "fatal": self.fatal_err
#         }
