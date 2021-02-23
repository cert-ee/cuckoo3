# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from pathlib import PureWindowsPath

def normalize_wincommandline(commandline, image_path):
    if not image_path:
        return ""

    return f"{PureWindowsPath(image_path).name} " \
           f"{commandline_args(commandline)}"

def commandline_args(commandline):
    if not commandline:
        return ""

    if commandline[0] in ("\"", "'"):
        end_quote = commandline[0]
        end_quote_index = commandline[1:].find(end_quote)
        if end_quote_index == -1:
            return ""
        else:
            return commandline[end_quote_index + 2:].lstrip()

    for char_index in range(len(commandline)):
        if commandline[char_index] in (" ", "\t", "\r", "\n"):
            return commandline[char_index:].lstrip()

    return ""

class ProcessStates:
    RUNNING = "running"
    TERMINATED = "terminated"

class Process:

    def __init__(self, pid, ppid, procid, image, commandline, start_ts,
                 state=ProcessStates.RUNNING, parent_procid=None,
                 tracked=True):
        self.pid = pid
        self.ppid = ppid
        self.procid = procid
        self.parent_procid = parent_procid
        self.image = image
        self.commandline = commandline
        self.start_ts = start_ts
        self.state = state
        self.tracked = tracked

        self.end_ts = None

    @property
    def process_name(self):
        return PureWindowsPath(self.image).name

    def set_terminated(self, end_ts):
        self.state = ProcessStates.TERMINATED
        self.end_ts = end_ts

    def mark_tracked(self):
        self.tracked = True

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
            "state": self.state,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts
        }

    def __str__(self):
        return f"<pid={self.pid}, ppid={self.ppid}, procid={self.procid}, " \
               f"parent_procid={self.parent_procid}, image={self.image}, " \
               f"state={self.state}>, tracked={self.tracked}"


class ProcessTracker:

    def __init__(self):
        self._pid_procid = {}
        self._pid_runningproc = {}
        self._procid_proc = {}

    def new_process(self, start_ts, pid, ppid, image, commandline,
                    tracked=True):

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
            pid, ppid, procid, image, commandline, start_ts,
            parent_procid=parent_procid, state=ProcessStates.RUNNING,
            tracked=tracked
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
        return self._procid_proc.get(procid)

    def lookup_procid(self, pid):
        return self._pid_procid.get(pid)

    def process_by_pid(self, pid):
        procid = self.lookup_procid(pid)
        if not procid:
            return None

        return self.lookup_process(procid)

    def set_tracked(self, pid):
        proc_id = self.lookup_procid(pid)
        if not proc_id:
            raise KeyError(
                f"Cannot set process with pid {pid} to tracked. "
                f"Pid is unknown."
            )

        process = self.lookup_process(proc_id)
        process.mark_tracked()

    def process_dictlist(self, tracked_only=True):
        plist = []
        for p in self._procid_proc.values():
            if tracked_only and not p.tracked:
                continue

            plist.append(p.to_dict())

        return plist
