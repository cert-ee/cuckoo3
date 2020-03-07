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
        self.fatal = {}

    def add_error(self, caller_instance, error):
        self.errors.append(f"{caller_instance.__class__.__name__}: {error}")

    def set_fatal_error(self, error, exception=False):
        if self.fatal:
            raise NotImplementedError(
                f"Fatal error cannot be overwritten. Content: {self.fatal}"
            )

        self.state = self.FATAL
        self.fatal = {
            "error": error,
            "traceback": traceback.format_exc() if exception else ""
        }

    def fatal_error(self, error):
        self.set_fatal_error(error, exception=False)
        raise CancelProcessing(error)

    def fatal_exception(self, error):
        self.set_fatal_error(error, exception=True)
        raise CancelProcessing(error)

    def to_dict(self):
        return {
            "errors": self.errors,
            "fatal": self.fatal
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
            "behavior": self.report_behavior
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

    def report_behavior(self):
        pass

    def cleanup(self):
        pass


def enumerate_plugins(package_path, namespace, class_,
                      attributes={}, as_dict=False):
    import os
    import importlib

    """Import plugins of type `class` located at `dirpath` into the
    `namespace` that starts with `module_prefix`. If `dirpath` represents a
    filepath then it is converted into its containing directory. The
    `attributes` dictionary allows one to set extra fields for all imported
    plugins. Using `as_dict` a dictionary based on the module name is
    returned."""

    try:
        dirpath = importlib.import_module(package_path).__file__
    except ImportError as e:
        raise ImportError(
            f"Unable to import plugins from package path: {package_path}. {e}"
        )
    if os.path.isfile(dirpath):
        dirpath = os.path.dirname(dirpath)

    for fname in os.listdir(dirpath):
        if fname.endswith(".py") and not fname.startswith("__init__"):
            module_name, _ = os.path.splitext(fname)
            try:
                importlib.import_module(
                    "%s.%s" % (package_path, module_name)
                )
            except ImportError as e:
                raise ImportError(
                    "Unable to load the Cuckoo plugin at %s: %s. Please "
                    "review its contents and/or validity!" % (fname, e)
                )

    subclasses = class_.__subclasses__()[:]

    plugins = []
    while subclasses:
        subclass = subclasses.pop(0)

        # Include subclasses of this subclass (there are some subclasses, e.g.,
        # LibVirtMachinery, that fail the fail the following module namespace
        # check and as such we perform this logic here).
        subclasses.extend(subclass.__subclasses__())

        # Check whether this subclass belongs to the module namespace that
        # we're currently importing. It should be noted that parent and child
        # namespaces should fail the following if-statement.
        if package_path != ".".join(subclass.__module__.split(".")[:-1]):
            continue

        namespace[subclass.__name__] = subclass
        for key, value in attributes.items():
            setattr(subclass, key, value)

        plugins.append(subclass)

    if as_dict:
        ret = {}
        for plugin in plugins:
            ret[plugin.__module__.split(".")[-1]] = plugin
        return ret

    return sorted(plugins, key=lambda x: x.__name__.lower())

def bytes_to_str(b):
    if isinstance(b, bytes):
        return b.decode()