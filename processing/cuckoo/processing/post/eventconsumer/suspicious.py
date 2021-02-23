# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.processing.abtracts import EventConsumer
from cuckoo.processing.event.events import Kinds, SuspiciousEvents
from cuckoo.processing.signatures.signature import Scores

class SuspiciousEventScoring(EventConsumer):

    event_types = (Kinds.SUSPICIOUS_EVENT,)

    event_handler = {}

    def init(self):
        # Each handler is a method that accepts an event and a process. It
        # must return a signature name, short description, score,
        # list of ioc dicts, list of TTPs, and a list of tags. In that order.
        # iocs, ttps, and tags can be an empty list
        self.event_handler = {
            SuspiciousEvents.DELETES_ITSELF: self._handle_deletesself,
            SuspiciousEvents.LOADS_DROPPED_DLL: self._handle_loaddll,
            SuspiciousEvents.EXECUTES_DROPPED_EXE: self._handle_execute_exe,
            SuspiciousEvents.NTCREATEPROCESS_OTHER_PARENT_PROCESS:
                self._handle_otherparent,
            SuspiciousEvents.NTCREATEPROCESSEX_OTHER_PARENT_PROCESS:
                self._handle_otherparent,
            SuspiciousEvents.NTCREATEUSERPROCESS_OTHER_PARENT_PROCESS:
                self._handle_otherparent,
            SuspiciousEvents.SETWINDOWSHOOKEX: self._handle_sethook,
            SuspiciousEvents.SETWINDOWSHOOKAW: self._handle_sethook,
            SuspiciousEvents.ENUMERATES_PROCESSES: self._handle_processenum,
            SuspiciousEvents.NTSETINFORMATIONTHREAD_HIDE_FROM_DEBUGGER:
                self._handle_hidefromdebugger,
            SuspiciousEvents.NTCREATETHREADEX_HIDE_FROM_DEBUGGER:
                self._handle_hidefromdebugger,
            SuspiciousEvents.LOADSDRIVER: self._handle_loaddriver,
            SuspiciousEvents.WRITEPROCESSMEMORY: self._handle_writeprocmem,
        }

    def _handle_deletesself(self, event, process):
        iocs = [{"path": process.image}]

        return (
            "deletes_itself", "Process deletes its own binary",
            Scores.SUSPICIOUS, iocs, ["T1070.004"], ["evasion"]
        )

    def _handle_loaddll(self, event, process):
        ioc = {}
        if len(event.args):
            ioc["path"] = event.args[0]

        return (
            "loads_dropped_dll", "Loads a dropped DLL", Scores.SUSPICIOUS,
            [ioc], [], []
        )

    def _handle_execute_exe(self, event, process):
        ioc = {}
        if len(event.args):
            ioc["path"] = event.args[0]

        return (
            "executes_dropped_exe", "Executes a dropped executable file",
            Scores.LIKELY_MALICIOUS, [ioc], [], []
        )

    def _handle_otherparent(self, event, process):
        ioc = {}
        if len(event.args):
            parent_proc = self.taskctx.process_tracker.process_by_pid(
                event.args[0]
            )
            if parent_proc:
                ioc = {
                    "parent_process": parent_proc.process_name,
                    "parent_process_id": parent_proc.procid
                }

        return (
            "process_other_parent",
            "Creates process with another process as the parent",
            Scores.KNOWN_BAD, [ioc], ["T1134.004"], ["evasion"]
        )

    def _handle_sethook(self, event, process):
        return (
            "creates_event_hook", "Creates an event hook", Scores.SUSPICIOUS,
            [], ["T1056.004"], []
        )

    def _handle_processenum(self, event, process):
        return (
            "enumerates_processes", "Enumerates existing processes",
            Scores.SUSPICIOUS, [], ["T1057"], []
        )

    def _handle_loaddriver(self, event, process):
        return (
            "loads_driver", "Loads a driver", Scores.SUSPICIOUS, [], [], []
        )

    def _handle_hidefromdebugger(self, event, process):
        return (
            "thread_hidefromdebugger",
            "Creates or hides an existing thread from debuggers",
            Scores.SUSPICIOUS, [], ["T1562.001"], ["evasion"]
        )

    def _handle_writeprocmem(self, event, process):
        ioc = {}
        if len(event.args):
            target_proc = self.taskctx.process_tracker.process_by_pid(
                event.args[0]
            )
            if target_proc:
                if target_proc.procid == process.procid:
                    return None

                ioc = {
                    "target_process": target_proc.process_name,
                    "target_process_id": target_proc.procid
                }

        return (
            "wrote_proc_memory", "Wrote to the memory of another process",
            Scores.INFORMATIONAL, [ioc], [], []
        )

    def _handle_default(self, event, process):
        return (
            f"susevent_{event.name.lower()}",
            f"Suspicious behavior detected: {event.name}",
            Scores.INFORMATIONAL, [], [], []
        )

    def use_event(self, event):
        process = self.taskctx.process_tracker.lookup_process(event.procid)

        # Retrieve handler for the suspicious event. If handler exists, use
        # the default handler. Handlers return the arguments for the signature
        # to trigger.
        handler = self.event_handler.get(event.name, self._handle_default)

        # The handler can return None in case an event should be skipped.
        sigfields = handler(event, process)
        if not sigfields:
            return

        signame, short_desc, score, iocs, ttps, tags = sigfields

        # Add extra process name and id field to each IoC
        if not iocs:
            iocs = [{"process": process.process_name,
                     "process_id": process.procid}]
        else:
            for ioc in iocs:
                ioc.update({
                    "process": process.process_name,
                    "process_id": process.procid
                })

        self.taskctx.signature_tracker.add_signature(
            name=signame, short_description=short_desc,
            description=event.description, ttps=ttps, tags=tags,
            score=score, iocs=iocs
        )
