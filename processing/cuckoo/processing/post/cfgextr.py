# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.storage import TaskPaths

from ..signatures.signature import Scores
from ..abtracts import Processor
from ..cfgextr.cfgextr import (
    Extractor, ConfigMemdump, ConfigExtractionError, UnexpectedDataError,
    ExtractedConfigTracker
)

class ProcMemCfgExtract(Processor):

    KEY = "cfgextr"

    @classmethod
    def init_once(cls):
        Extractor.init_once()

    def start(self):
        dumps = os.listdir(TaskPaths.procmem_dump(self.ctx.task.id))
        if not dumps:
            return

        tracker = ExtractedConfigTracker()
        for dump in dumps:
            if not ConfigMemdump.valid_name(dump):
                continue

            with ConfigMemdump(
                    TaskPaths.procmem_dump(self.ctx.task.id, dump)
            ) as confdump:

                try:
                    Extractor.search(confdump, tracker)
                except UnexpectedDataError as e:
                    self.ctx.log.warning(
                        "Failure during config extraction",
                        dumpname=confdump.name, error=e
                    )

        if not tracker.configs:
            return

        for config in tracker.configs:
            self.ctx.signature_tracker.add_signature(
                Scores.KNOWN_BAD,
                name=f"Malware configuration {config.family}",
                short_description=f"Extracted malware configuration of "
                                  f"known family: {config.family}",
                family=config.family,
                iocs=[{"dump": dump} for dump in config.sources]
            )


        return [config.to_dict() for config in tracker.configs]
