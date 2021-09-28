# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

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
    CATEGORY = []

    def __init__(self, processingctx):
        self.ctx = processingctx

    @classmethod
    def enabled(cls):
        return True

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
    CATEGORY = []

    def __init__(self, processingctx):
        self.ctx = processingctx

        self.handlers = {}

        # Build a mapping of stage:handlermethod. Only add the method for
        # the stage if the method of our current instance is implemented.
        for stage, method in (("identification", self.report_identification),
                              ("pre", self.report_pre_analysis),
                              ("post", self.report_post_analysis)):
            if method.__func__ is not getattr(
                    Reporter, method.__func__.__name__
            ):
                self.handlers[stage] = method

    @classmethod
    def enabled(cls):
        return True

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

class LogFileTranslator:
    """The abstract class each logfile (logs/) reader must implement"""

    name = ""
    supports = ("",)

    def __init__(self, log_path, taskctx):
        self.log_path = log_path
        self._taskctx = taskctx
        self._fp = None

    @classmethod
    def handles(cls, filename):
        if filename.lower() in cls.supports:
            return True
        return False

    def read_events(self):
        """Yields normalized events from the logfile"""
        raise NotImplementedError

    def _open_log(self):
        self._fp = open(self.log_path, "rb")

    def _close_log(self):
        if self._fp:
            self._fp.close()

    def __enter__(self):
        self._open_log()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_log()

class EventConsumer:

    ORDER = 999
    event_types = ()
    CATEGORY = []

    def __init__(self, task_context):
        self.taskctx = task_context

    @classmethod
    def enabled(cls):
        return True

    @classmethod
    def init_once(cls):
        pass

    def init(self):
        pass

    def use_event(self, event):
        raise NotImplementedError

    def finalize(self):
        pass

    def cleanup(self):
        pass
