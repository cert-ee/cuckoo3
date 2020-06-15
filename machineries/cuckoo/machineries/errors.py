# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class MachineryError(Exception):
    pass

class MachineryConnectionError(MachineryError):
    pass

class MachineryUnhandledStateError(MachineryError):
    pass

class MachineNotFoundError(MachineryError):
    pass

class MachineUnexpectedStateError(MachineryError):
    pass

class MachineStateReachedError(MachineryError):
    pass

class MachineryManagerClientError(Exception):
    pass

class ResponseTimeoutError(MachineryManagerClientError):
    pass
