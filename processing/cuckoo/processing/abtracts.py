# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

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


    def __init__(self, analysis, analysis_path, logger,
                 identification=None, task_id=None, submitted_file=None):
        self.analysis_path = analysis_path
        self.analysis = analysis
        self.analysislog = logger

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

    def __init__(self, analysis, analysis_path, logger,
                 identification=None, task_id=None, submitted_file=None):
        self.analysis_path = analysis_path
        self.analysis = analysis
        self.analysislog = logger

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
