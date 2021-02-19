# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from google.protobuf import message

from cuckoo.processing import abtracts

from cuckoo.processing.event import registrytools, processtools, filetools
from . import (
    file_pb2, inject_pb2, mutant_pb2, network_pb2, process_pb2, registry_pb2,
    suspicious_pb2
)
from cuckoo.processing.event.events import (
    File, FileActions, Process, ProcessStatuses, Registry, RegistryActions,
    RegistryValueTypes, REGISTRY_ACTION_EFFECT, ProcessInjection,
    ProcessInjectActions, NetworkFlow, Mutant, MutantActions, SuspiciousEvent,
    SuspiciousEvents
)

_FILE_ACTION_TRANSLATE = {
    file_pb2.OpenRead: FileActions.OPEN_READ,
    file_pb2.OpenModify: FileActions.OPEN_MODIFY,
    file_pb2.CreateRead: FileActions.CREATE_READ,
    file_pb2.CreateModify: FileActions.CREATE_MODIFY,
    file_pb2.Delete: FileActions.DELETE,
    file_pb2.Rename: FileActions.RENAME,
    file_pb2.Truncate: FileActions.TRUNCATE
}

def _translate_file_event(threemon_file, ctx):
    normalized_action = _FILE_ACTION_TRANSLATE.get(threemon_file.kind)

    # If event is not normalized, fall back to the name of the file access
    # event declared in the pb event format file.
    if not normalized_action:
        normalized_action = file_pb2.FileAccess.Name(threemon_file.kind)

    if threemon_file.id:
        ctx.file_ids.add_path(threemon_file.id, threemon_file.srcpath)

    return File(
        ts=threemon_file.ts, action=normalized_action,
        pid=threemon_file.pid,
        procid=ctx.processes.lookup_procid(threemon_file.pid),
        srcpath=threemon_file.srcpath, dstpath=threemon_file.dstpath,
        status=threemon_file.status,
        srcpath_normalized=filetools.normalize_winpath(threemon_file.srcpath),
        dstpath_normalized=filetools.normalize_winpath(threemon_file.dstpath)
    )


_PROCESS_STATUS_TRANSLATE = {
    process_pb2.Existing: ProcessStatuses.EXISTING,
    process_pb2.Ignore: ProcessStatuses.IGNORED,
    process_pb2.Create: ProcessStatuses.CREATED,
    process_pb2.Terminate: ProcessStatuses.TERMINATED
}

def _translate_process_event(threemon_process, ctx):
    normalized_status = _PROCESS_STATUS_TRANSLATE.get(threemon_process.status)
    if not normalized_status:
        return None

    if normalized_status == ProcessStatuses.TERMINATED:
        procid, parent_procid = ctx.processes.terminated_process(
            threemon_process.ts, threemon_process.pid
        )
    elif normalized_status in (ProcessStatuses.EXISTING,
                               ProcessStatuses.IGNORED,
                               ProcessStatuses.CREATED):
        procid, parent_procid = ctx.processes.new_process(
            threemon_process.ts, threemon_process.pid, threemon_process.ppid,
            threemon_process.image, threemon_process.command,
            tracked=normalized_status==ProcessStatuses.CREATED
        )
    else:
        raise ValueError(f"Unexpected process state: {normalized_status}")

    return Process(
        ts=threemon_process.ts, status=normalized_status,
        pid=threemon_process.pid, ppid=threemon_process.ppid,
        procid=procid, parentprocid=parent_procid,
        image=threemon_process.image, commandline=threemon_process.command,
        exit_code=threemon_process.exit_status,
        commandline_normalized=processtools.normalize_wincommandline(
            threemon_process.command, threemon_process.image
        )
    )

_REGISTRY_ACTION_TRANSLATE = {
    registry_pb2.CreateKey: RegistryActions.CREATE_KEY,
    registry_pb2.CreateKeyEx: RegistryActions.CREATE_KEY_EX,
    registry_pb2.DeleteKey: RegistryActions.DELETE_KEY,
    registry_pb2.EnumerateKey: RegistryActions.ENUMERATE_KEY,
    registry_pb2.EnumerateValueKey: RegistryActions.ENUMERATE_VALUE_KEY,
    registry_pb2.LoadKey: RegistryActions.LOADKEY,
    registry_pb2.OpenKey: RegistryActions.OPEN_KEY,
    registry_pb2.OpenKeyEx: RegistryActions.OPEN_KEY_EX,
    registry_pb2.QueryKey: RegistryActions.QUERY_KEY,
    registry_pb2.QueryKeySecurity: RegistryActions.QUERY_KEY_SECURITY,
    registry_pb2.QueryMultipleValueKey: RegistryActions.QUERY_MULTIPLE_VALUE_KEY,
    registry_pb2.QueryValueKey: RegistryActions.QUERY_VALUE_KEY,
    registry_pb2.RenameKey: RegistryActions.RENAME_KEY,
    registry_pb2.SetInformationKey: RegistryActions.SET_INFORMATION_KEY,
    registry_pb2.SetKeySecurity: RegistryActions.SET_KEY_SECURITY,
    registry_pb2.UnloadKey: RegistryActions.UNLOAD_KEY,
    registry_pb2.DeleteValueKey: RegistryActions.DELETE_VALUE_KEY,
    registry_pb2.SetValueKeyInt: RegistryActions.SET_VALUE,
    registry_pb2.SetValueKeyStr: RegistryActions.SET_VALUE,
    registry_pb2.SetValueKeyDat: RegistryActions.SET_VALUE
}

reg_read_ignore = (
    "\\clsid",
    "\\wow6432node\\clsid",
    "\\wow6432node\\interface",
    "\\software\\classes\\allfilesystemobjects",
    "\\software\\classes\\directory",
    "\\software\\classes\\folder",
    "\\software\\classes\\interface\\",
    "\\software\\classes\\wow6432node\\interface\\",
    "\\software\\classes\\clsid\\",
    "\\software\\classes\\wow6432node\\clsid\\",
    "\\software\\classes\\appid\\",
    "\\software\\classes\\wow6432node\\appid\\",
    "\\software\\classes\\internetshortcut\\",
)

hives = (
    "\\registry\\machine",
    "\\registry\\user"
)

reg_read_ignorellist = tuple(
    [f"{hive}{key}" for hive in hives for key in reg_read_ignore]
)

def remove_user_id(k):
    k = k.lower()
    if not k.startswith("\\registry\\user\\s-"):
        return k

    offset = 15
    while offset < len(k):
        if k[offset] == "\\":
            break
        offset += 1

    return f"{k[:14]}{k[offset:]}"

def ignoredlisted_key(k):
    return remove_user_id(k).startswith(reg_read_ignorellist)

def _translate_registry_event(threemon_registry, ctx):
    normalized_action = _REGISTRY_ACTION_TRANSLATE.get(threemon_registry.kind)

    # If event is not normalized, fall back to the name of the file access
    # event declared in the pb event format file.
    if not normalized_action:
        normalized_action = registry_pb2.RegistryKind.Name(
            threemon_registry.kind
        )

    if threemon_registry.kind == registry_pb2.SetValueKeyInt:
        valuetype = RegistryValueTypes.INTEGER
        val = int(threemon_registry.valuei)
    elif threemon_registry.kind == registry_pb2.SetValueKeyStr:
        valuetype = RegistryValueTypes.STRING
        val = threemon_registry.values
    elif threemon_registry.kind == registry_pb2.SetValueKeyDat:
        valuetype = RegistryValueTypes.BINARY
        val = threemon_registry.valued
    else:
        valuetype = ""
        val = None

        if REGISTRY_ACTION_EFFECT.get(normalized_action, "") == "key_read":
            if ignoredlisted_key(threemon_registry.path):
                return None


    return Registry(
        ts=threemon_registry.ts, action=normalized_action,
        status=threemon_registry.status, pid=threemon_registry.pid,
        procid=ctx.processes.lookup_procid(threemon_registry.pid),
        path=threemon_registry.path, value=val, valuetype=valuetype,
        path_normalized=registrytools.normalize_winregistry(
            threemon_registry.path
        )
    )

_INJECTION_ACTION_TRANSLATE = {
    inject_pb2.CreateRemoteThread: ProcessInjectActions.CREATE_REMOTE_THREAD,
    inject_pb2.ShellTrayWindow: ProcessInjectActions.SHELL_TRAYWINDOW,
    inject_pb2.QueueUserAPC: ProcessInjectActions.QUEUE_USER_APC
}

def _translate_injection_event(threemon_injection, ctx):
    normalized_action = _INJECTION_ACTION_TRANSLATE.get(
        threemon_injection.technique
    )

    # If event is not normalized, fall back to the name of the injection
    # event declared in the pb event format file.
    if not normalized_action:
        normalized_action = inject_pb2.Technique.Name(
            threemon_injection.technique
        )

    # Mark the injected process as tracked, since it is now under control
    # of whatever injected it.
    ctx.processes.set_tracked(threemon_injection.dstpid)

    return ProcessInjection(
        ts=threemon_injection.ts, action=normalized_action,
        pid=threemon_injection.srcpid,
        procid=ctx.processes.lookup_procid(threemon_injection.srcpid),
        dstpid=threemon_injection.dstpid,
        dstprocid=ctx.processes.lookup_procid(threemon_injection.dstpid)
    )

def _translate_networkflow_event(threemon_netflow, ctx):
    return NetworkFlow(
        ts=threemon_netflow.ts, pid=threemon_netflow.pid,
        proto_number=threemon_netflow.proto,
        procid=ctx.processes.lookup_procid(threemon_netflow.pid),
        srcip=threemon_netflow.srcip, srcport=threemon_netflow.srcport,
        dstip=threemon_netflow.dstip, dstport=threemon_netflow.dstport
    )


_MUTANT_ACTION_TRANSLATE = {
    mutant_pb2.MutantCreate: MutantActions.CREATE,
    mutant_pb2.MutantOpen: MutantActions.OPEN
}

def _translate_mutant_event(threemon_mutant, ctx):
    normalized_action = _MUTANT_ACTION_TRANSLATE.get(threemon_mutant.action)
    if not normalized_action:
        return

    return Mutant(
        ts=threemon_mutant.ts, action=normalized_action,
        status=threemon_mutant.status, pid=threemon_mutant.pid,
        procid=ctx.processes.lookup_procid(threemon_mutant.pid),
        path=threemon_mutant.path
    )

_SUSPICIOUS_EVENT_TRANSLATE = {
    suspicious_pb2.UnmapMainImage: SuspiciousEvents.UNMAPMAINIMAGE,
    suspicious_pb2.NtCreateThreadExHideFromDebugger: SuspiciousEvents.NTCREATETHREADEX_HIDE_FROM_DEBUGGER,
    suspicious_pb2.NtSetInformationThreadHideFromDebugger: SuspiciousEvents.NTSETINFORMATIONTHREAD_HIDE_FROM_DEBUGGER,
    suspicious_pb2.NtCreateProcessOtherParentProcess: SuspiciousEvents.NTCREATEUSERPROCESS_OTHER_PARENT_PROCESS,
    suspicious_pb2.NtCreateProcessExOtherParentProcess: SuspiciousEvents.NTCREATEPROCESSEX_OTHER_PARENT_PROCESS,
    suspicious_pb2.NtCreateUserProcessOtherParentProcess: SuspiciousEvents.NTCREATEUSERPROCESS_OTHER_PARENT_PROCESS,
    suspicious_pb2.SetWindowsHookAW: SuspiciousEvents.SETWINDOWSHOOKAW,
    suspicious_pb2.SetWindowsHookEx: SuspiciousEvents.SETWINDOWSHOOKEX,
    suspicious_pb2.AdjustPrivilegeToken: SuspiciousEvents.ADJUSTPRIVILEGETOKEN,
    suspicious_pb2.DeletesItself: SuspiciousEvents.DELETES_ITSELF,
    suspicious_pb2.LoadsDroppedDLL: SuspiciousEvents.LOADS_DROPPED_DLL,
    suspicious_pb2.ExecutesDroppedEXE: SuspiciousEvents.EXECUTES_DROPPED_EXE,
    suspicious_pb2.WriteProcessMemory: SuspiciousEvents.WRITEPROCESSMEMORY,
    suspicious_pb2.SetThreadContext: SuspiciousEvents.SETTHREADCONTEXT,
    suspicious_pb2.EnumeratesProcesses: SuspiciousEvents.ENUMERATES_PROCESSES,
    suspicious_pb2.MapViewOfSection: SuspiciousEvents.MAPVIEWOFSECTION,
    suspicious_pb2.LoadsDriver: SuspiciousEvents.LOADSDRIVER
}

def _translate_suspicious_event(threemon_suspicious, ctx):
    normalized = _SUSPICIOUS_EVENT_TRANSLATE.get(threemon_suspicious.event)
    if not normalized:
        normalized = suspicious_pb2.SuspiciousEvent.Name(
            threemon_suspicious.event
        )

    args = []
    if threemon_suspicious.arg1:
        args.append(threemon_suspicious.arg1)
    if threemon_suspicious.arg2:
        args.append(threemon_suspicious.arg2)

    if normalized == SuspiciousEvents.EXECUTES_DROPPED_EXE:
        args[0] = ctx.file_ids.get_path(threemon_suspicious.arg1)

    return SuspiciousEvent(
        ts=threemon_suspicious.ts, eventname=normalized,
        pid=threemon_suspicious.pid,
        procid=ctx.processes.lookup_procid(threemon_suspicious.pid),
        args=tuple(args)
    )


_kindmap = {
    1: (process_pb2.Process, _translate_process_event),
    2: (registry_pb2.Registry, _translate_registry_event),
    3: (suspicious_pb2.Suspicious, _translate_suspicious_event),
    # 5: (notification_pb2.Notification,),
    6: (inject_pb2.Inject, _translate_injection_event),
    8: (file_pb2.File, _translate_file_event),
    9: (mutant_pb2.Mutant, _translate_mutant_event),
    # 10: (thread_pb2.ThreadContext,),
    12: (network_pb2.NetworkFlow, _translate_networkflow_event),
    # 14: (whois_pb2.Whois,),
    # 15: (vminfo_pb2.Vminfo,),
    # 16: (mutant_pb2.Event,),
    # 126: (debug_pb2.Debug,)
}


class _FileIdTracker:

    def __init__(self):
        self._files = {}

    def get_path(self, file_id):
        return self._files.get(file_id, "")

    def add_path(self, file_id, path):
        self._files[file_id] = path

    def clear(self):
        self._files = {}

class _TranslateContext:

    def __init__(self, process_tracker):
        self.processes = process_tracker
        self.file_ids = _FileIdTracker()

    def close(self):
        self.file_ids.clear()


class ThreemonReader(abtracts.LogFileTranslator):

    name = "Threemon reader"
    supports = ("threemon.pb",)

    def read_events(self):
        buffreader = self._fp
        translate_context = _TranslateContext(self._taskctx.process_tracker)
        while True:
            start_offset = buffreader.tell()
            header = buffreader.read(4)
            if not header:
                buffreader.seek(start_offset)
                break

            if not len(header) == 4:
                buffreader.seek(start_offset)
                break

            data_size = sum(b * (256**i) for i, b in enumerate(header[:3]))
            kind = int(header[3])

            decoder_normalizer = _kindmap.get(kind)
            if not decoder_normalizer or len(decoder_normalizer) != 2:
                # Unsupported event kind. Skip the amount of bytes equal to
                # the event data size. The header bytes are already read.
                buffreader.seek(buffreader.tell() + data_size)
                continue

            data = buffreader.read(data_size)
            if len(data) != data_size:
                buffreader.seek(start_offset)
                break

            kind_instance = decoder_normalizer[0]()

            try:
                kind_instance.ParseFromString(data)
            except message.DecodeError as e:
                self._taskctx.log.warning(
                    "Threemon protobuf decoding error", error=e
                )
                continue

            try:
                normalized = decoder_normalizer[1](
                    kind_instance, translate_context
                )
            except ValueError as e:
                self._taskctx.log.warning(
                    "Threemon event translation error in translator handler",
                    error=e, handler=decoder_normalizer[1]
                )
                continue

            if normalized:
                yield normalized

        translate_context.close()
