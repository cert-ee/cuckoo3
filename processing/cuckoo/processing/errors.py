# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class CancelProcessing(Exception):
    pass

class CancelReporting(Exception):
    pass

class PluginError(Exception):
    pass

class DisablePluginError(Exception):
    pass

class PluginWorkerError(Exception):
    pass

class StaticAnalysisError(Exception):
    pass
