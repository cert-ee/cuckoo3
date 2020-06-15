# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import traceback

class CancelProcessing(Exception):
    pass

class ErrorTracker:
    """A tracker instance made for each processing phase of an analysis.
    The instance should be passed to processing modules and lastly, the
    reporting modules should write it to disk."""

    OK = "OK"
    FATAL = "fatal"

    def __init__(self):
        self.state = self.OK
        self.errors = []
        self.fatal_err = {}

    def add_error(self, caller_instance, error):
        self.errors.append(f"{caller_instance.__class__.__name__}: {error}")

    def set_fatal_error(self, error, exception=False):
        if self.fatal_err:
            raise NotImplementedError(
                f"Fatal error cannot be overwritten. Content: {self.fatal_err}"
            )

        self.state = self.FATAL
        self.fatal_err = {
            "error": error,
            "traceback": traceback.format_exc() if exception else ""
        }

    def fatal_error(self, error):
        self.set_fatal_error(error, exception=False)
        raise CancelProcessing(error)

    def fatal_exception(self, error):
        self.set_fatal_error(error, exception=True)
        raise CancelProcessing(error)

    def has_errors(self):
        return len(self.errors) > 0 or len(self.fatal_err) > 0

    def to_dict(self):
        return {
            "errors": self.errors,
            "fatal": self.fatal_err
        }

class Processor:
    """Abstract for a module that performs some kind of processing for an
    analysis or task.

    Attributes
        ORDER: Determines the order in which all modules are ran.
    """

    NAME = ""
    ORDER = 999
    KEY = ""

    # TODO Plugins that are only useful for specific platforms. Do the same
    # for file types/tags?
    PLATFORMS = []
    CATEGORY = ["file", "url"]


    def __init__(self, analysis, analysis_path,
                 identification=None, task_id=None, submitted_file=None):
        self.analysis_path = analysis_path
        self.analysis = analysis

        self.submitted_file = submitted_file
        self.identification = identification
        self.task_id = task_id

        self.results = {}

        self.errtracker = None

    def set_results(self, results):
        self.results = results

    def set_errortracker(self, tracker):
        self.errtracker = tracker

    @classmethod
    def init_once(cls):
        pass

    def init(self):
        pass

    def start(self):
        raise NotImplementedError

    def cleanup(self):
        pass

class Reporter:
    """Abstract for a module that performs some kind of results storing for an
    analysis or task.

    Attributes
        ORDER: Determines the order in which all modules are ran.
    """

    ORDER = 999

    def __init__(self, analysis, analysis_path,
                 identification=None, task_id=None, submitted_file=None):
        self.analysis_path = analysis_path
        self.analysis = analysis

        self.submitted_file = submitted_file
        self.identification = identification
        self.task_id = task_id

        self.results = {}

        self.errtracker = None

        self.handlers = {
            "identification": self.report_identification,
            "pre": self.report_pre_analysis,
            "behavior": self.report_post_analysis
        }

    def set_results(self, results):
        self.results = results

    def set_errortracker(self, tracker):
        self.errtracker = tracker

    @classmethod
    def init_once(cls):
        pass

    def init(self):
        pass

    def report_identification(self):
        pass

    def report_pre_analysis(self):
        pass

    def report_post_analysis(self):
        pass

    def cleanup(self):
        pass

def bytes_to_str(b):
    if isinstance(b, bytes):
        return b.decode()