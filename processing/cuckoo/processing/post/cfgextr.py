# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os

from cuckoo.common.packages import enumerate_plugins
from cuckoo.common.storage import TaskPaths

from ..abtracts import Processor
from ..cfgextr.cfgextr import (
    ConfigMemdump,
    ConfigExtractionError,
    ExtractedConfigTracker,
    ExtractedConfig,
    ConfigExtractor,
    UnexpectedDataError,
)
from ..signatures.signature import Scores, IOC


class ProcMemCfgExtract(Processor):
    KEY = "cfgextr"

    @classmethod
    def init_once(cls):
        cls.extractors = enumerate_plugins(
            "cuckoo.processing.cfgextr", globals(), ConfigExtractor
        )

    def _run_extractors(self, confdump, tracker):
        for extractor in self.extractors:
            extracted = ExtractedConfig(extractor.FAMILY, confdump.name)
            try:
                extractor.search(confdump, extracted)
            except UnexpectedDataError as e:
                self.ctx.log.warning(
                    "Unexpected data during extraction",
                    extractor=extractor,
                    dump=confdump.name,
                    error=e,
                )

            if not extracted.detected:
                continue

            tracker.add_config(extracted)

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
                    self._run_extractors(confdump, tracker)
                except ConfigExtractionError as e:
                    self.ctx.log.warning(
                        "Failure during config extraction",
                        dumpname=confdump.name,
                        error=e,
                    )

        if not tracker.configs:
            return

        for config in tracker.configs:
            if not config.values:
                self.ctx.signature_tracker.add_signature(
                    Scores.KNOWN_BAD,
                    name=f"{config.family} malware data structure",
                    short_description=f"Detected known malware family data "
                    f"structure in memory: {config.family}",
                    family=config.family,
                )

            else:
                self.ctx.signature_tracker.add_signature(
                    Scores.KNOWN_BAD,
                    name=f"Malware configuration {config.family}",
                    short_description=f"Extracted malware configuration of "
                    f"known family: {config.family}",
                    family=config.family,
                    iocs=[IOC(**{"dump": dump}) for dump in config.sources],
                )

        configs = [config.to_dict() for config in tracker.configs if config.values]

        if configs:
            return configs
