# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.


class MachineryError(Exception):
    pass


class MachineryConnectionError(MachineryError):
    pass


class MachineryUnhandledStateError(MachineryError):
    pass


class MachineryDependencyError(MachineryError):
    pass


class MachineNotFoundError(MachineryError):
    pass


class MachineUnexpectedStateError(MachineryError):
    pass


class MachineStateReachedError(MachineryError):
    pass


class MachineNetCaptureError(MachineryError):
    pass
