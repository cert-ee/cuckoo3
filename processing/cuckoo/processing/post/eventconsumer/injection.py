# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.processing.abtracts import EventConsumer
from cuckoo.processing.event.events import Kinds
from cuckoo.processing.signatures.signature import Scores

class ProcessInjection(EventConsumer):

    event_types = (Kinds.PROCESS_INJECTION,)

    def use_event(self, event):
        srcproc = self.taskctx.process_tracker.lookup_process(event.procid)
        dstproc = self.taskctx.process_tracker.lookup_process(event.dstprocid)

        self.taskctx.signature_tracker.add_signature(
            name="process_injection", short_description="Process injection",
            description="Process injection is a method of executing arbitrary "
                        "code in the address space a separate live process.",
            ttps=["T1055"], tags=["evasion"], score=Scores.KNOWN_BAD,
            iocs=[{
                "technique": event.description,
                "source_process": srcproc.process_name,
                "source_procid": srcproc.procid,
                "destination_process": dstproc.process_name,
                "destination_procid": dstproc.procid
            }]
        )
