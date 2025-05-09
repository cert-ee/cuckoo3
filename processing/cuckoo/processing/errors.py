# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.


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
