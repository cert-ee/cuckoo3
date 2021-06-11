# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import base64

class Kinds:
    FILE = "file"
    PROCESS = "process"
    REGISTRY = "registry"
    PROCESS_INJECTION = "process_injection"
    NETFLOW = "networkflow"
    MUTANT = "mutant"
    SUSPICIOUS_EVENT = "suspicious_event"

class NormalizedEvent:

    __slots__ = ("ts", "description", "effect")
    dictdump = ("ts", "kind", "effect")
    kind = ""

    def to_dict(self):
        return {k: getattr(self, k) for k in self.dictdump}

    def pattern_scan(self, pattern_scanner, processing_ctx):
        pass

class FileActions:
    OPEN_READ = "open_read"
    OPEN_MODIFY = "open_modify"
    CREATE_READ = "create_read"
    CREATE_MODIFY = "create_modify"
    DELETE = "delete"
    RENAME = "rename"
    TRUNCATE = "truncate"

FILE_ACTION_DESC = {
    FileActions.OPEN_READ: "Opened file read-only",
    FileActions.OPEN_MODIFY: "Opened file for modifying",
    FileActions.CREATE_READ: "Created file read-only",
    FileActions.CREATE_MODIFY: "Created file",
    FileActions.DELETE: "Deleted file",
    FileActions.RENAME: "Renamed file",
    FileActions.TRUNCATE: "Truncated file"
}

_FILE_ACTION_EFFECT = {
    FileActions.OPEN_READ: "file_read",
    FileActions.OPEN_MODIFY: "file_written",
    FileActions.CREATE_READ: "file_created",
    FileActions.CREATE_MODIFY: "file_created",
    FileActions.TRUNCATE: "file_deleted",
    FileActions.DELETE: "file_deleted",
    FileActions.RENAME: "file_renamed",
}

_FILE_ACTION_SIMPLIFIED = {
    FileActions.OPEN_READ: "read",
    FileActions.OPEN_MODIFY: "write",
    FileActions.CREATE_READ: "write",
    FileActions.CREATE_MODIFY: "write",
    FileActions.TRUNCATE: "delete",
    FileActions.DELETE: "delete",
    FileActions.RENAME: "rename",
}

class File(NormalizedEvent):

    __slots__ = ("action", "pid", "procid", "srcpath", "dstpath", "status",
                 "srcpath_normalized", "dstpath_normalized")
    dictdump = NormalizedEvent.dictdump + (
        "action", "pid", "procid", "srcpath", "dstpath"
    )
    kind = Kinds.FILE

    def __init__(self, ts, action, pid, procid, srcpath, dstpath,
                 status, srcpath_normalized, dstpath_normalized):
        self.ts = ts
        self.action = action
        self.pid = pid
        self.procid = procid
        self.srcpath = srcpath
        self.dstpath = dstpath
        self.srcpath_normalized = srcpath_normalized
        self.dstpath_normalized = dstpath_normalized

        self.status = status

        self.effect = _FILE_ACTION_EFFECT.get(action, "file_read")
        self.description = FILE_ACTION_DESC.get(action, "")

    def pattern_scan(self, pattern_scanner, processing_ctx):
        if self.action == FileActions.RENAME:
            pattern_scanner.scan(
                self.dstpath_normalized, self.dstpath, self, self.kind,
                processing_ctx=processing_ctx,
                event_subtype=f"{_FILE_ACTION_SIMPLIFIED.get(self.action)} dst"
            )
            pattern_scanner.scan(
                self.dstpath_normalized, self.srcpath, self, self.kind,
                processing_ctx=processing_ctx,
                event_subtype=f"{_FILE_ACTION_SIMPLIFIED.get(self.action)} src"
            )
        else:
            pattern_scanner.scan(
                self.srcpath_normalized, self.srcpath, self, self.kind,
                processing_ctx=processing_ctx,
                event_subtype=_FILE_ACTION_SIMPLIFIED.get(self.action)
            )

class ProcessStatuses:
    EXISTING = "existing"
    IGNORED = "ignored"
    CREATED = "created"
    TERMINATED = "terminated"

PROCESS_STATUS_DESC = {
    ProcessStatuses.EXISTING: "Existing process",
    ProcessStatuses.IGNORED: "Ignored process",
    ProcessStatuses.CREATED: "Created process",
    ProcessStatuses.TERMINATED: "Terminated process"
}

PROCESS_ACTION_EFFECT = {
    ProcessStatuses.CREATED: "process_created",
    ProcessStatuses.TERMINATED: "process_terminated"
}

class Process(NormalizedEvent):

    __slots__ = (
        "status", "pid", "ppid", "procid", "parentprocid", "image",
        "commandline", "exit_code", "commandline_normalized"
    )
    dictdump = NormalizedEvent.dictdump + (
        "status", "pid", "ppid", "procid", "parentprocid", "image",
        "commandline", "exit_code"
    )
    kind = Kinds.PROCESS

    def __init__(self, ts, status, pid, ppid, procid, parentprocid,
                 image, commandline, exit_code, commandline_normalized):
        self.ts = ts
        self.status = status
        self.pid = pid
        self.ppid = ppid
        self.procid = procid
        self.parentprocid = parentprocid
        self.image = image
        self.commandline = commandline
        self.commandline_normalized = commandline_normalized
        self.exit_code = exit_code

        self.description = PROCESS_STATUS_DESC.get(status, "")
        self.effect = PROCESS_ACTION_EFFECT.get(status, "")

    def pattern_scan(self, pattern_scanner, processing_ctx):
        if self.status != ProcessStatuses.CREATED:
            return

        pattern_scanner.scan(
            self.commandline_normalized, self.commandline, self, "commandline",
            processing_ctx=processing_ctx
        )


class RegistryActions:
    CREATE_KEY = "create_key"
    CREATE_KEY_EX = "create_key_ex"
    DELETE_KEY = "delete_key"
    ENUMERATE_KEY = "enumerate_key"
    ENUMERATE_VALUE_KEY = "enumerate_value_key"
    LOADKEY = "load_key"
    OPEN_KEY = "open_key"
    OPEN_KEY_EX = "open_key_ex"
    QUERY_KEY = "query_key"
    QUERY_KEY_SECURITY = "query_key_security"
    QUERY_MULTIPLE_VALUE_KEY = "query_multiple_value_key"
    QUERY_VALUE_KEY = "query_value_key"
    RENAME_KEY = "rename_key"
    SET_INFORMATION_KEY = "set_information_key"
    SET_KEY_SECURITY = "set_key_security"
    UNLOAD_KEY = "unload_key"
    DELETE_VALUE_KEY = "delete_value_key"
    SET_VALUE = "set_value"

class RegistryValueTypes:
    INTEGER = "Integer"
    STRING = "String"
    BINARY = "Binary"


REGISTRY_ACTION_DESC = {
    RegistryActions.CREATE_KEY: "Created registry key",
    RegistryActions.CREATE_KEY_EX: "Created registry key",
    RegistryActions.DELETE_KEY: "Deleted registry key",
    RegistryActions.ENUMERATE_KEY: "Enumerated registry key",
    RegistryActions.ENUMERATE_VALUE_KEY: "Enumerated registry key value",
    RegistryActions.LOADKEY: "Loaded registry key",
    RegistryActions.OPEN_KEY: "Opened registry key",
    RegistryActions.OPEN_KEY_EX: "Opened registry key",
    RegistryActions.QUERY_KEY: "Queried registry key",
    RegistryActions.QUERY_KEY_SECURITY: "Queried registry key security",
    RegistryActions.QUERY_MULTIPLE_VALUE_KEY: "Queried registry key value",
    RegistryActions.QUERY_VALUE_KEY: "Queried registry key value",
    RegistryActions.RENAME_KEY: "Renamed registry key",
    RegistryActions.SET_INFORMATION_KEY: "Set registry key information",
    RegistryActions.SET_KEY_SECURITY: "Set registry key security",
    RegistryActions.UNLOAD_KEY: "Unloaded registry key",
    RegistryActions.DELETE_VALUE_KEY: "Deleted registry key value",
    RegistryActions.SET_VALUE: "Set registry key value"
}

REGISTRY_ACTION_EFFECT = {
    RegistryActions.CREATE_KEY: "key_created",
    RegistryActions.CREATE_KEY_EX: "key_created",
    RegistryActions.LOADKEY: "key_created",
    RegistryActions.ENUMERATE_KEY: "key_read",
    RegistryActions.ENUMERATE_VALUE_KEY: "key_read",
    RegistryActions.OPEN_KEY: "key_read",
    RegistryActions.OPEN_KEY_EX: "key_read",
    RegistryActions.QUERY_KEY: "key_read",
    RegistryActions.QUERY_KEY_SECURITY: "key_read",
    RegistryActions.QUERY_MULTIPLE_VALUE_KEY: "key_read",
    RegistryActions.QUERY_VALUE_KEY: "key_read",
    RegistryActions.RENAME_KEY: "key_renamed",
    RegistryActions.SET_INFORMATION_KEY: "key_written",
    RegistryActions.SET_KEY_SECURITY: "key_written",
    RegistryActions.SET_VALUE: "key_written",
    RegistryActions.UNLOAD_KEY: "key_deleted",
    RegistryActions.DELETE_VALUE_KEY: "key_deleted",
    RegistryActions.DELETE_KEY: "key_deleted",
}

_REGISTRY_ACTION_SIMPLIFIED= {
    RegistryActions.CREATE_KEY: "write",
    RegistryActions.CREATE_KEY_EX: "write",
    RegistryActions.LOADKEY: "write",
    RegistryActions.ENUMERATE_KEY: "read",
    RegistryActions.ENUMERATE_VALUE_KEY: "read",
    RegistryActions.OPEN_KEY: "read",
    RegistryActions.OPEN_KEY_EX: "read",
    RegistryActions.QUERY_KEY: "read",
    RegistryActions.QUERY_KEY_SECURITY: "read",
    RegistryActions.QUERY_MULTIPLE_VALUE_KEY: "read",
    RegistryActions.QUERY_VALUE_KEY: "read",
    RegistryActions.RENAME_KEY: "rename",
    RegistryActions.SET_INFORMATION_KEY: "write",
    RegistryActions.SET_KEY_SECURITY: "write",
    RegistryActions.SET_VALUE: "write",
    RegistryActions.UNLOAD_KEY: "delete",
    RegistryActions.DELETE_VALUE_KEY: "delete",
    RegistryActions.DELETE_KEY: "delete",
}

class Registry(NormalizedEvent):

    __slots__ = (
        "action", "status", "pid", "procid", "path", "value", "valuetype",
        "path_normalized"
    )
    dictdump = NormalizedEvent.dictdump + (
        "action", "status", "pid", "procid", "path", "valuetype"
    )
    kind = Kinds.REGISTRY

    def __init__(self, ts, action, status, pid, procid, path, value,
                 valuetype, path_normalized):
        self.ts = ts
        self.action = action
        self.status = status
        self.pid = pid
        self.procid = procid
        self.path = path
        self.path_normalized = path_normalized
        self.value = value
        self.valuetype = valuetype

        self.effect = REGISTRY_ACTION_EFFECT.get(action, "key_read")
        self.description = REGISTRY_ACTION_DESC.get(action, "")

    def pattern_scan(self, pattern_scanner, processing_ctx):
        pattern_scanner.scan(
            self.path_normalized, self.path, self, self.kind,
            event_subtype=_REGISTRY_ACTION_SIMPLIFIED.get(self.action),
            processing_ctx=processing_ctx
        )

        if self.action == RegistryActions.SET_VALUE:
            value = None
            humanval = None
            # Cast ints to strings, as the scan engine wants strings or bytes
            if self.valuetype == RegistryValueTypes.INTEGER:
                value = str(self.value)
                humanval = value

            # Encode the value that will be presented with base64, so it
            # can be used in a JSON report and the original value can be
            # decoded if needed.
            if self.valuetype == RegistryValueTypes.BINARY:
                humanval = base64.b64encode(self.value).decode()

            pattern_scanner.scan(
                value if value is not None else self.value,
                humanval if humanval is not None else self.value,
                self, self.kind, event_subtype="value",
                extra_safelistdata=[(self.path_normalized, ("write",))],
                processing_ctx=processing_ctx
            )


class ProcessInjectActions:
    CREATE_REMOTE_THREAD = "create_remote_thread"
    SHELL_TRAYWINDOW = "shell_traywindow"
    QUEUE_USER_APC = "queue_user_apc"

INJECTION_ACTION_DESC = {
    ProcessInjectActions.CREATE_REMOTE_THREAD: "Process injection by creating "
                                               "a remote thread in the "
                                               "destination process",
    ProcessInjectActions.SHELL_TRAYWINDOW: "Process injection "
                                           "(ShellTrayWindow)",
    ProcessInjectActions.QUEUE_USER_APC: "Process injection by adding a "
                                         "user-mode APC to destination "
                                            "process thread APC queue."
}

class ProcessInjection(NormalizedEvent):

    __slots__ = ("action", "pid", "procid", "dstpid", "dstprocid",)
    dictdump = NormalizedEvent.dictdump + __slots__
    kind = Kinds.PROCESS_INJECTION

    def __init__(self, ts, action, pid, procid, dstpid, dstprocid):
        self.ts = ts
        self.action = action
        self.pid = pid
        self.procid = procid
        self.dstpid = dstpid
        self.dstprocid = dstprocid

        self.effect = "process_injection"
        self.description = INJECTION_ACTION_DESC.get(action, "")

class NetworkFlow(NormalizedEvent):

    kind = Kinds.NETFLOW

    def __init__(self, ts, pid, procid, proto_number, srcip, srcport, dstip,
                 dstport):
        self.ts = ts
        self.pid = pid
        self.procid = procid
        self.proto_number = proto_number
        self.scrip = srcip
        self.srcport = srcport
        self.dstip = dstip
        self.dstport = dstport

        self.description = ""
        self.effect = "network_flow"


class MutantActions:
    CREATE = "create"
    OPEN = "open"

MUTANT_ACTION_DESC = {
    MutantActions.CREATE: "Created mutant",
    MutantActions.OPEN: "Opened mutant"
}

_MUTANT_ACTION_EFFECT = {
    MutantActions.CREATE: "mutant_created",
    MutantActions.OPEN: "mutant_opened"
}

_MUTANT_ACTION_SIMPLIFIED = {
    MutantActions.CREATE: "created",
    MutantActions.OPEN: "open"
}


class Mutant(NormalizedEvent):

    __slots__ = ("action", "status", "pid", "procid", "path",)
    dictdump = NormalizedEvent.dictdump + __slots__
    kind = Kinds.MUTANT

    def __init__(self, ts, action, status, pid, procid, path):
        self.ts = ts
        self.action = action
        self.status = status
        self.pid = pid
        self.procid = procid
        self.path = path

        self.description = MUTANT_ACTION_DESC.get(action, "")
        self.effect = _MUTANT_ACTION_EFFECT.get(action, "")

    def pattern_scan(self, pattern_scanner, processing_ctx):
        pattern_scanner.scan(
            self.path, self.path, self, "mutant",
            event_subtype=_MUTANT_ACTION_SIMPLIFIED.get(self.action),
            processing_ctx=processing_ctx
        )


class SuspiciousEvents:
    UNMAPMAINIMAGE = "UnmapMainImage"
    NTCREATETHREADEX_HIDE_FROM_DEBUGGER = "NtCreateThreadExHideFromDebugger"
    NTSETINFORMATIONTHREAD_HIDE_FROM_DEBUGGER = \
        "NtSetInformationThreadHideFromDebugger"
    NTCREATEPROCESS_OTHER_PARENT_PROCESS = "NtCreateProcessOtherParentProcess"
    NTCREATEPROCESSEX_OTHER_PARENT_PROCESS = \
        "NtCreateProcessExOtherParentProcess"
    NTCREATEUSERPROCESS_OTHER_PARENT_PROCESS = \
        "NtCreateUserProcessOtherParentProcess"
    SETWINDOWSHOOKAW = "SetWindowsHookAW"
    SETWINDOWSHOOKEX = "SetWindowsHookEx"
    ADJUSTPRIVILEGETOKEN = "AdjustPrivilegeToken"
    DELETES_ITSELF = "DeletesItself"
    LOADS_DROPPED_DLL = "LoadsDroppedDLL"
    EXECUTES_DROPPED_EXE = "ExecutesDroppedEXE"
    WRITEPROCESSMEMORY = "WriteProcessMemory"
    SETTHREADCONTEXT = "SetThreadContext"
    ENUMERATES_PROCESSES = "EnumeratesProcesses"
    MAPVIEWOFSECTION = "MapViewOfSection"
    LOADSDRIVER = "LoadsDriver"



SUSPICIOUS_EVENT_DESCRIPTION = {
    SuspiciousEvents.UNMAPMAINIMAGE: "Process unmapped its own process image.",
    SuspiciousEvents.NTSETINFORMATIONTHREAD_HIDE_FROM_DEBUGGER: "Set HIDE_FROM_DEBUGGER flag for a thread.",
    SuspiciousEvents.NTCREATETHREADEX_HIDE_FROM_DEBUGGER: "Created thread with HIDE_FROM_DEBUGGER flag.",
    SuspiciousEvents.NTCREATEPROCESS_OTHER_PARENT_PROCESS: "Created a process with a different parent than the creating process.",
    SuspiciousEvents.NTCREATEPROCESSEX_OTHER_PARENT_PROCESS: "Created a process with a different parent than the creating process.",
    SuspiciousEvents.NTCREATEUSERPROCESS_OTHER_PARENT_PROCESS: "Created a process with a different parent than the creating process.",
    SuspiciousEvents.SETWINDOWSHOOKAW: "A new event hook was created. Often used by malware to log key strokes or to check for user interaction as part of anti-VM tactics.",
    SuspiciousEvents.SETWINDOWSHOOKEX: "A new event hook was created. Often used by malware to log key strokes or to check for user interaction as part of anti-VM tactics.",
    SuspiciousEvents.ADJUSTPRIVILEGETOKEN: "A privilege for an access token was adjusted. Windows uses the token to control the ability of the user to perform various system-related operations.",
    SuspiciousEvents.DELETES_ITSELF: "The process deleted its own executable",
    SuspiciousEvents.LOADS_DROPPED_DLL: "A dropped DLL was loaded.",
    SuspiciousEvents.EXECUTES_DROPPED_EXE: "A process was created using a dropped executable.",
    SuspiciousEvents.WRITEPROCESSMEMORY: "A process wrote data to an area of memory in another process.",
    SuspiciousEvents.SETTHREADCONTEXT: "",
    SuspiciousEvents.ENUMERATES_PROCESSES: "Enumerates processes. Could be anti-VM behavior.",
    SuspiciousEvents.MAPVIEWOFSECTION: "",
    SuspiciousEvents.LOADSDRIVER: "A driver was loaded."
}


class SuspiciousEvent(NormalizedEvent):

    __slots__ = ("name", "pid", "procid", "args")
    dictdump = NormalizedEvent.dictdump + __slots__
    kind = Kinds.SUSPICIOUS_EVENT

    def __init__(self, ts, eventname, pid, procid, args):
        self.ts = ts
        self.name = eventname
        self.pid = pid
        self.procid = procid
        self.args = args

        self.description = SUSPICIOUS_EVENT_DESCRIPTION.get(eventname, "")
        self.effect = ""

    def pattern_scan(self, pattern_scanner, processing_ctx):
        pattern_scanner.scan(
            self.name.lower(), self.name, self, "suspicious_event",
            processing_ctx=processing_ctx
        )
