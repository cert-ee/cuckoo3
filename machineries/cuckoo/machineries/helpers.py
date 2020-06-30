# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from threading import Lock

class MachineStates:

    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    POWEROFF = "poweroff"
    RESTORED = "restored"
    SUSPENDED = "suspended"
    ERROR = "error"

class Machine:

    def __init__(self, name, label, ip, platform, os_version, tags,
                  snapshot=None, mac_address="", machinery=None,
                 state="UNKNOWN",  locked=False, locked_by="", reserved=False,
                 reserved_by="", disabled=False, disabled_reason="",
                 errors=[]):

        # Configuration information
        self.name = name
        self.label = label
        self.ip = ip
        self.platform = platform
        self.os_version = os_version
        self.tags = tags
        self.snapshot = snapshot
        self.mac_address = mac_address
        self.interface = ""

        self.machinery = machinery

        # Restorable information
        self.reserved = reserved
        self.reserved_by = reserved_by

        # Reset every object creation
        self.state = state
        self.locked = locked
        self.locked_by = locked_by

        self.disabled = disabled
        self.disable_reason = disabled_reason

        self.errors = errors

        # Lock that is acquired when a machine manager worker thread
        # is about to perform an action on a machine.
        self.action_lock = Lock()

    @property
    def available(self):
        return not self.disabled and not self.locked and not self.reserved

    @property
    def unavailable_reason(self):
        if self.available:
            return ""

        if self.disabled:
            return f"Machine is disabled. Reason: {self.disable_reason}"
        if self.reserved:
            return f"Machine is reserved by {self.reserved_by}"
        if self.locked:
            return f"Machine is locked by: {self.locked_by}"

        return "Machine is unavailable for unknown reasons"

    @property
    def machinery_name(self):
        if not self.machinery:
            return ""

        return self.machinery.name

    def lock(self, task_id):
        self.locked = True
        self.locked_by = task_id

    def clear_lock(self):
        self.locked_by = ""
        self.locked = False

    def disable(self, reason):
        self.disabled = True
        self.disable_reason = reason

    def reserve(self, task_id):
        self.reserved = True
        self.reserved_by = task_id

    def clear_reservation(self):
        self.reserved = False
        self.reserved_by = ""

    def add_error(self, error):
        self.errors.append(error)

    def load_stored_states(self, machine):
        """Read attributes from a given machine helper and copy the values
        to the current machine helper instance"""
        self.reserved = machine.reserved
        self.reserved_by = machine.reserved_by

    def to_dict(self):
        if isinstance(self.tags, set):
            tags = list(self.tags)
        else:
            tags = self.tags
        return {
            "name": self.name,
            "label": self.label,
            "ip": self.ip,
            "platform": self.platform,
            "os_version": self.os_version,
            "tags": tags,
            "snapshot": self.snapshot,
            "mac_address": self.mac_address,
            "machinery_name": self.machinery_name,
            "state": self.state,
            "locked": self.locked,
            "locked_by": self.locked_by,
            "reserved": self.reserved,
            "reserved_by": self.reserved_by,
            "disabled": self.disabled,
            "disabled_reason": self.disable_reason,
            "errors": self.errors
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d["name"], label=d["label"], ip=d["ip"],
            platform=d["platform"], os_version=d["os_version"],
            tags=set(d["tags"]), snapshot=d["snapshot"], machinery=None,
            state=d["state"], locked=d["locked"], locked_by=d["locked_by"],
            reserved=d["reserved"], reserved_by=d["reserved_by"],
            disabled=d["disabled"], disabled_reason=d["disabled_reason"],
            errors=d["errors"]
        )
