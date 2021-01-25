# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.storage import TaskPaths

from ..signatures.signature import Scores
from ..abtracts import Processor
from ..cfgextr.cfgextr import (
    Extractor, ConfigMemdump, ConfigExtractionError, UnexpectedDataError
)

class ProcMemCfgExtract(Processor):

    KEY = "cfgextr"

    @classmethod
    def init_once(cls):
        Extractor.init_once()

    def start(self):
        configs = []

        for dumppath in os.listdir(TaskPaths.procmem_dump(self.ctx.task.id)):
            if not ConfigMemdump.valid_name(dumppath):
                continue

            with ConfigMemdump(
                    TaskPaths.procmem_dump(self.ctx.task.id, dumppath)
            ) as confdump:

                try:
                    extracted = Extractor.search(confdump)
                except UnexpectedDataError as e:
                    self.ctx.log.warning(
                        "Failure during config extraction",
                        dumpname=confdump.name, error=e
                    )

                if extracted:
                    configs.append(extracted)

        for config in configs:
            self.ctx.signature_tracker.add_signature(
                Scores.KNOWN_BAD,
                name=f"Malware configuration {config.family}",
                short_description=f"Extracted malware configuration of "
                                  f"known family: {config.family}",
                family=config.family, iocs=[{"dump": confdump.name}]
            )

        if configs:
            return [config.to_dict() for config in configs]
