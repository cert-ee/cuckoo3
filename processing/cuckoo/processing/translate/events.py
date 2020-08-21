# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class Kinds:
    FILE = "file"
    PROCESS = "process"
    REGISTRY = "registry"
    PROCESS_INJECTION = "process_injection"
    NETFLOW = "networkflow"
    MUTANT = "mutant"

class NormalizedEvent:

    __slots__ = ("ts", "description", "effect")
    dictdump = ("ts", "kind", "effect")
    kind = ""

    def to_dict(self):
        return {k: getattr(self, k) for k in self.dictdump}


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


class File(NormalizedEvent):

    __slots__ = ("action", "pid", "procid", "srcpath", "dstpath", "status")
    dictdump = NormalizedEvent.dictdump + (
        "action", "pid", "procid", "srcpath", "dstpath"
    )
    kind = Kinds.FILE

    def __init__(self, ts, action, pid, procid, srcpath, dstpath,
                 status):
        self.ts = ts
        self.action = action
        self.pid = pid
        self.procid = procid
        self.srcpath = srcpath
        self.dstpath = dstpath
        self.status = status

        self.effect = _FILE_ACTION_EFFECT.get(action, "file_read")
        self.description = FILE_ACTION_DESC.get(action, "")

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
        "commandline", "exit_code"
    )
    dictdump = NormalizedEvent.dictdump + __slots__
    kind = Kinds.PROCESS

    def __init__(self, ts, status, pid, ppid, procid, parentprocid,
                 image, commandline, exit_code):
        self.ts = ts
        self.status = status
        self.pid = pid
        self.ppid = ppid
        self.procid = procid
        self.parentprocid = parentprocid
        self.image = image
        self.commandline = commandline
        self.exit_code = exit_code

        self.description = PROCESS_STATUS_DESC.get(status, "")
        self.effect = PROCESS_ACTION_EFFECT.get(status, "")


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

class Registry(NormalizedEvent):

    __slots__ = (
        "action", "status", "pid", "procid", "path", "value", "valuetype"
    )
    dictdump = NormalizedEvent.dictdump + (
        "action", "status", "pid", "procid", "path", "valuetype"
    )
    kind = Kinds.REGISTRY

    def __init__(self, ts, action, status, pid, procid, path, value,
                 valuetype):
        self.ts = ts
        self.action = action
        self.status = status
        self.pid = pid
        self.procid = procid
        self.path = path
        self.value = value
        self.valuetype = valuetype

        self.effect = REGISTRY_ACTION_EFFECT.get(action, "key_read")
        self.description = REGISTRY_ACTION_DESC.get(action, "")


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
