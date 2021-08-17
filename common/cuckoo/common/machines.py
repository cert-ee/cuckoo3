# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import json
import threading
from datetime import datetime, timedelta

from .log import CuckooGlobalLogger
from .storage import safe_json_dump

log = CuckooGlobalLogger(__name__)

class MachineListError(Exception):
    pass

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
                 machinery_name="", errors=[], architecture="",
                 interface=""):

        # Configuration information
        self.name = name
        self.label = label
        self.ip = ip
        self.platform = platform
        self.os_version = os_version
        self.tags = tags
        self.snapshot = snapshot
        self.mac_address = mac_address
        self.architecture = architecture
        self.interface = interface

        self.machinery = machinery
        if machinery:
            self.machinery_name = machinery.name
        else:
            self.machinery_name = machinery_name

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
            "architecture": self.architecture,
            "interface": self.interface,
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

    def copy(self):
        return self.from_dict(self.to_dict())

    @classmethod
    def from_file(cls, filepath):
        try:
            with open(filepath, "r") as fp:
                d = json.load(fp)
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f"JSON decoding error: {e}")

        return cls.from_dict(d)

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d["name"], label=d["label"], ip=d["ip"],
            platform=d["platform"], os_version=d["os_version"],
            tags=set(d["tags"]), snapshot=d["snapshot"],
            architecture=d["architecture"], interface=d["interface"],
            machinery=None, state=d["state"], locked=d["locked"],
            locked_by=d["locked_by"], reserved=d["reserved"],
            reserved_by=d["reserved_by"], disabled=d["disabled"],
            disabled_reason=d["disabled_reason"], errors=d["errors"],
            machinery_name=d["machinery_name"],
        )


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
        else:
            raise TypeError(
                f"tags must be a set of strings. Not {type(tags)}")

    matches = []
    for machine in find_in:
        if tags.issubset(machine.tags):
            matches.append(machine)

    return matches

class MachinesList:

    def __init__(self):
        # Machine object instances
        self._machines = []

        # This lock must be acquired when making any changes to the
        # machines list or any of its members.
        self._machines_lock = threading.RLock()

        # Should be set to true if anything in the machine list changed
        # machine state, new machine, lock/unlock, etc.
        self._updated = False

        # Has any machine ever been added to this list
        self.loaded = False

    @property
    def available_count(self):
        with self._machines_lock:
            c = 0
            for machine in self._machines:
                if machine.available:
                    c += 1

            return c

    @property
    def updated(self):
        return self._updated

    @property
    def machines(self):
        return self._machines

    def add_machine(self, machine):
        self._machines.append(machine)
        self.loaded = True
        self.set_updated()

    def count(self):
        return len(self._machines)

    def copy(self):
        newlist = MachinesList()
        for machine in self._machines:
            newlist.add_machine(machine.copy())

        return newlist

    def get_by_name(self, name):
        """Return the machine that matches the machine name.
        Raises KeyError if the machine is not found."""
        for machine in self._machines:
            if machine.name == name:
                return machine

        raise KeyError(f"Machine with name {name} does not exist")

    def get_available(self):
        """Return a list of all machines that are available for
        analysis tasks"""
        available = []
        for machine in self._machines:
            if machine.available:
                available.append(machine)

        return available

    def find(self, platform="", os_version="", tags=set()):
        """Find any machine that matches the given platform, version and
        has the given tags."""
        if not self._machines:
            return None

        machines = self._machines
        if platform:
            machines = find_platform(machines, platform, os_version)
            if not machines:
                return None

        if tags:
            machines = find_tags(machines, tags)
            if not machines:
                return None

        return machines[0]

    def find_available(self, name="", platform="", os_version="", tags=set()):
        """Find an available machine by name or platform, os_version, and tags.
        return None if no available machine is found."""
        if name:
            machine = self.get_by_name(name)
            if not machine.available:
                return None

            return machine

        machines = self.get_available()
        if not machines:
            return None

        if platform:
            machines = find_platform(machines, platform, os_version)
            if not machines:
                return None

        if tags:
            machines = find_tags(machines, tags)
            if not machines:
                return None

        return machines[0]

    def get_platforms_versions(self):
        platforms_versions = {}

        for machine in self._machines:
            versions = platforms_versions.setdefault(machine.platform, set())
            if machine.os_version:
                versions.add(machine.os_version)

        return platforms_versions

    def _lock_machine(self, machine, task_id):
        """Lock the given machine for the given task_id. This makes the machine
        unavailable for acquiring."""
        with self._machines_lock:
            if not machine.available:
                raise MachineListError(
                    f"Machine {machine.name} is unavailable and cannot be "
                    f"locked. {machine.unavailable_reason}"
                )
            machine.lock(task_id)
            self.set_updated()

    def set_state(self, machine, state):
        """Set the given machine to the given state"""
        with self._machines_lock:
            machine.state = state
            self.set_updated()

    def set_updated(self):
        self._updated = True

    def clear_updated(self):
        self._updated = False

    def acquire_available(self, task_id, name="", platform="", os_version="",
                          tags=set()):
        """Find and lock a machine for task_id that matches the given name or
        platform, os_version, and has the given tags."""
        with self._machines_lock:
            machine = self.find_available(
                name, platform, os_version, tags
            )

            if not machine:
                return None

            self._lock_machine(machine, task_id)
            return machine

    def release(self, machine):
        """Unlock the given machine to put it back in the pool of available
        machines"""
        with self._machines_lock:
            if not machine.locked:
                raise MachineListError(
                    f"Cannot unlock machine {machine.name}. Machine is not "
                    f"locked."
                )

            machine.clear_lock()
            self.set_updated()

    def mark_disabled(self, machine, reason):
        """Mark the machine as disabled. Causing it to no longer be available.
        Should be used if machines reach an unexpected state."""
        with self._machines_lock:
            machine.disable(reason)
            self.set_state(machine, States.ERROR)

class MachineListDumper:
    """Simple helper to to keep track of when a dump of all added machine
    lists was last made. min_dump_wait is a number in seconds."""

    def __init__(self, min_dump_wait=300):
        self.lists = set()

        self._min_dump_wait = min_dump_wait
        self._last_dump = None
        self._lists_changed = False

    def lists_changed(self):
        for mlist in self.lists:
            if mlist.updated:
                return True

        return False

    def dump_wait_reached(self):
        if not self._last_dump:
            return True

        if datetime.utcnow() - self._last_dump >= timedelta(
                seconds=self._min_dump_wait
        ):
            return True

        return False

    def should_dump(self):
        return self.dump_wait_reached() and self.lists_changed() \
               or self._lists_changed

    def make_dump(self, path):
        dump_machine_lists(path, *self.lists)
        self._last_dump = datetime.utcnow()

        self._lists_changed = False
        for mlist in self.lists:
            mlist.clear_updated()

    def add_machinelist(self, machine_list):
        self.lists.add(machine_list)
        self._lists_changed = True

    def remove_machinelist(self, machine_list):
        self.lists.discard(machine_list)
        self._lists_changed = True


def find_in_lists(machine_lists, name="", platform="", os_version="",
                  tags=set()):
    for machines in machine_lists:
        if name:
            try:
                return machines.get_by_name(name)
            except KeyError:
                continue

        machine = machines.find(
            platform=platform, os_version=os_version, tags=tags
        )
        if machine:
            return machine

    return None

def serialize_machinelists(*machine_lists):
    machines = []
    for machine_list in machine_lists:
        machines.extend([
            machine.to_dict() for machine in machine_list.machines
        ])
    return machines

def dump_machine_lists(path, *args):
    machines = []
    for machinelist in args:
        machines.extend([
            machine.to_dict() for machine in machinelist.machines
        ])

    # This is required to prevent the machine info dump from ever being
    # empty. The function ensures the file is first being dumped and afterwards
    # replaces the existing dump.
    safe_json_dump(path, machines, overwrite=True)


def read_machines_dump_dict(dump):
    machinelist = MachinesList()

    for machine_dict in dump:
        try:
            machinelist.add_machine(Machine.from_dict(machine_dict))
        except KeyError as e:
            raise MachineListError(
                f"Incomplete machine in dump. Missing key: {e}"
            )
    return machinelist

def read_machines_dump(path):
    with open(path, "r") as fp:
        return read_machines_dump_dict(json.load(fp))
