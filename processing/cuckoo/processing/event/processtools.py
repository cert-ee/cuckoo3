# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from pathlib import PureWindowsPath


class UnknownProcessError(Exception):
    pass


def normalize_wincommandline(commandline, image_path):
    if not image_path:
        return ""

    return f"{PureWindowsPath(image_path).name} {commandline_args(commandline)}"


def normalize_winimage(image_path):
    if not image_path:
        return ""

    path = image_path.lower()
    if (
        len(path) >= 7
        and path[5] == ":"
        and path[6] == "\\"
        and path.startswith("\\??\\")
    ):
        return path[4:]

    return path


def commandline_args(commandline):
    if not commandline:
        return ""

    if commandline[0] in ('"', "'"):
        end_quote = commandline[0]
        end_quote_index = commandline[1:].find(end_quote)
        if end_quote_index == -1:
            return ""
        else:
            return commandline[end_quote_index + 2 :].lstrip()

    for char_index in range(len(commandline)):
        if commandline[char_index] in (" ", "\t", "\r", "\n"):
            return commandline[char_index:].lstrip()

    return ""


def is_windowserr_svc(process):
    return process.commandline == "C:\\Windows\\System32\\svchost.exe -k WerSvcGroup"


class ProcessStates:
    RUNNING = "running"
    TERMINATED = "terminated"


class Process:
    def __init__(
        self,
        pid,
        ppid,
        procid,
        image,
        commandline,
        start_ts,
        state=ProcessStates.RUNNING,
        parent_procid=None,
        tracked=True,
    ):
        self.pid = pid
        self.ppid = ppid
        self.procid = procid
        self.parent_procid = parent_procid
        self.image = image
        self.normalized_image = normalize_winimage(image)
        self.commandline = commandline
        self.start_ts = start_ts
        self.state = state
        self.tracked = tracked
        self.injected = False

        self.end_ts = None

    @property
    def process_name(self):
        return PureWindowsPath(self.image).name

    def set_terminated(self, end_ts):
        self.state = ProcessStates.TERMINATED
        self.end_ts = end_ts

    def mark_tracked(self):
        self.tracked = True

    def mark_injected(self):
        self.injected = True

    def to_dict(self):
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "procid": self.procid,
            "parent_procid": self.parent_procid,
            "image": self.image,
            "name": self.process_name,
            "commandline": self.commandline,
            "tracked": self.tracked,
            "injected": self.injected,
            "state": self.state,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
        }

    def __str__(self):
        return (
            f"<pid={self.pid}, ppid={self.ppid}, procid={self.procid}, "
            f"parent_procid={self.parent_procid}, image={self.image}, "
            f"state={self.state}>, tracked={self.tracked}"
        )


class ProcessTracker:
    def __init__(self):
        self._pid_procid = {}
        self._pid_runningproc = {}
        self._procid_proc = {}

    def new_process(self, start_ts, pid, ppid, image, commandline, tracked=True):
        parent = self._pid_runningproc.get(ppid)

        # Set the parent to None/unknown if its parent is not known to us as
        # a running process. We assume the monitor log is in time ascending
        # order, meaning a terminated process cannot be the parent.
        if parent:
            parent_procid = parent.procid
        else:
            parent_procid = None

        procid = len(self._procid_proc) + 1
        process = Process(
            pid,
            ppid,
            procid,
            image,
            commandline,
            start_ts,
            parent_procid=parent_procid,
            state=ProcessStates.RUNNING,
            tracked=tracked,
        )

        self._pid_procid[pid] = procid
        self._pid_runningproc[pid] = process
        self._procid_proc[procid] = process

        return procid, parent_procid

    def terminated_process(self, stop_ts, pid):
        process = self._pid_runningproc.pop(pid, None)

        # Should never happen if are aware of all processes that existed
        # upon monitor tool load and afterwards.
        if not process:
            return None, None

        process.set_terminated(stop_ts)
        self._pid_procid.pop(process.pid, None)

        return process.procid, process.parent_procid

    def lookup_process(self, procid):
        if procid not in self._procid_proc:
            raise UnknownProcessError(f"No process with procid {procid}")

        return self._procid_proc[procid]

    def lookup_procid(self, pid):
        try:
            return self._pid_procid[pid]
        except KeyError:
            raise UnknownProcessError(f"Unknown process with PID: {pid}")

    def process_by_pid(self, pid):
        procid = self.lookup_procid(pid)
        if not procid:
            return None

        return self.lookup_process(procid)

    def set_tracked(self, pid, injected=False):
        proc_id = self.lookup_procid(pid)
        if not proc_id:
            raise UnknownProcessError(
                f"Cannot set process with pid {pid} to tracked. Pid is unknown."
            )

        process = self.lookup_process(proc_id)
        process.mark_tracked()
        if injected:
            process.mark_injected()

    def process_dictlist(self, tracked_only=True):
        plist = []
        for p in self._procid_proc.values():
            if tracked_only and not p.tracked:
                continue

            plist.append(p.to_dict())

        return plist

    def to_dict(self, tracked_only=True, max_processes=100):
        proclist = self.process_dictlist(tracked_only=tracked_only)
        truncated = False
        process_count = len(proclist)
        if process_count > max_processes:
            proclist = proclist[0:max_processes]
            truncated = True

        return {
            "truncated": truncated,
            "count": process_count,
            "process_list": proclist,
        }
