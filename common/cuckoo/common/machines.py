# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import threading

from .log import CuckooGlobalLogger
from .storage import safe_json_dump

log = CuckooGlobalLogger(__name__)

class States:
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
        self.action_lock = threading.Lock()

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

    def to_file(self, path):
        with open(path, "w") as fp:
            json.dump(self.to_dict(), fp, indent=2)

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

# Machine object instances mapping to their machine name. This module
# searches this data.
_machines = {}

def read_machines_dump(path):
    loaded = {}
    with open(path, "r") as fp:
        machines = json.load(fp)

    for name, machine_dict in machines.items():
        machine = Machine.from_dict(machine_dict)
        loaded[name] = machine

    return loaded

def set_machines_dump(dump):
    if not isinstance(dump, dict):
        raise TypeError("Dump must be a dictionary")

    global _machines
    _machines = dump

def machines_loaded():
    if _machines:
        return True
    return False

def add_machine(machine):
    _machines[machine.name] = machine

def dump_machines_info(path):
    """Dump the json version of each loaded machine (_machines) to the given
    path"""
    dump = {}
    for name, machine in _machines.items():
        dump[name] = machine.to_dict()

    # This is required vto prevent the machine info dump from ever being
    # empty. The function ensures the file is first being dumped and afterwards
    # replaces the existing dump.
    safe_json_dump(path, dump, overwrite=True)

def find(platform="", os_version="", tags=set()):
    """Find any machine that matches the given platform, version and
    has the given tags."""
    machines = list(_machines.values())
    if not machines:
        return None

    if platform:
        machines = find_platform(
            machines, platform, os_version
        )
        if not machines:
            return None

    if tags:
        machines = find_tags(machines, tags)
        if not machines:
            return None

    return machines[0]

def find_available(name="", platform="", os_version="", tags=set()):
    """Find an available machine by name or platform, os_version, and tags.
    return None if no available machine is found."""
    if name:
        machine = get_by_name(name)
        if not machine.available:
            return None

        return machine

    machines = get_available()
    if not machines:
        return None

    if platform:
        machines = find_platform(
            machines, platform, os_version
        )
        if not machines:
            return None

    if tags:
        machines = find_tags(machines, tags)
        if not machines:
            return None

    return machines[0]

def get_available():
    """Return a list of all machines that are available for analysis tasks"""
    available = []
    for machine in _machines.values():
        if machine.available:
            available.append(machine)

    return available

def get_by_name(name):
    """Return the machine that matches the machine name.
    Raises KeyError if the machine is not found."""
    try:
        return _machines[name]
    except KeyError as e:
        raise KeyError(
            f"Machine with name {name} does not exist."
        ).with_traceback(e.__traceback__)

def find_platform(find_in, platform, os_version=""):
    """Find all machines with the specified platform and version in the
     list of machines given."""
    matches = []
    for machine in find_in:
        if machine.platform == platform:
            if os_version and machine.os_version != os_version:
                continue

            matches.append(machine)

    return matches

def find_tags(find_in, tags):
    """Find all machines that have the specified tags in the list
    of machines given. Tags must be a set."""
    if not isinstance(tags, set):
        if isinstance(tags, (list, tuple)):
            tags = set(tags)

        raise TypeError(f"tags must be a set of strings. Not {type(tags)}")

    matches = []
    for machine in find_in:
        if tags.issubset(machine.tags):
            matches.append(machine)

    return matches

def count():
    return len(_machines)
