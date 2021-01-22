# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.storage import TaskPaths

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

            with ConfigMemdump(dumppath) as confdump:

                try:
                    extracted = Extractor.search(confdump)
                except UnexpectedDataError as e:
                    self.ctx.log.warning(
                        "Failure during config extraction",
                        dumpname=confdump.name, error=e
                    )

                if extracted:
                    configs.append(extracted)

        if configs:
            return [config.to_dict() for config in configs]
