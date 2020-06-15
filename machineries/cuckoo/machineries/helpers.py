# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import time

from collections import namedtuple
from uuid import uuid4
from threading import Lock

from cuckoo.common.ipc import UnixSockClient, NotConnectedError

from .errors import MachineryManagerClientError, ResponseTimeoutError

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
        self.locked = True

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

class MachineryManagerClient(UnixSockClient):

    _Response = namedtuple("_Response", ["success", "msg_id", "reason"])

    def __init__(self, sockpath):
        super().__init__(sockpath, blockingreads=False)
        self._responses = {}

    def _store_response(self, response):
        self._responses[response.msg_id] = response

    def _wait_response(self, msg_id, timeout):
        waited = 0
        sleep_length = 1
        while True:
            if waited > timeout:
                raise ResponseTimeoutError()

            response = self.get_response(msg_id)

            if response is not None:
                return response

            waited += sleep_length
            time.sleep(sleep_length)

    def get_response(self, msg_id):
        try:
            json_msg = self.recv_json_message()
        except NotConnectedError:
            raise MachineryManagerClientError("Client not connected")

        if json_msg:
            try:
                self._store_response(self._Response(
                    success=json_msg["success"], msg_id=json_msg["msg_id"],
                    reason=json_msg.get("reason", "")
                ))
            except KeyError as e:
                raise MachineryManagerClientError(
                    f"Response {repr(json_msg)} does not contain "
                    f"mandatory key {e}"
                )

        response = self._responses.pop(msg_id, None)
        if not response:
            return None

        return response

    def machine_action(self, action, machine_name,
                       wait_response=True, timeout=120):
        msg_id = str(uuid4())
        self.send_json_message({
            "msg_id": msg_id,
            "action": action,
            "machine": machine_name
        })

        if not wait_response:
            return msg_id

        return self._wait_response(msg_id, timeout)

    def restore_start(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "restore_start", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def norestore_start(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "norestore_start", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def stop(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "stop", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def acpi_stop(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "acpi_stop", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def memory_dump(self, machine_name, wait_response=True, timeout=120):
        raise NotImplementedError()
