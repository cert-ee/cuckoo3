# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.storage import Paths

from cuckoo.processing.abtracts import EventConsumer
from cuckoo.processing.errors import PluginError
from cuckoo.processing.event.events import Kinds
from cuckoo.processing.signatures.pattern import (
    PatternScanner, PatternSignatureError
)

log = CuckooGlobalLogger(__name__)

class PatternFinder(EventConsumer):

    event_types = (Kinds.FILE, Kinds.REGISTRY, Kinds.PROCESS, Kinds.MUTANT)

    platform_scanner = {}

    @classmethod
    def init_once(cls):
        def add_sigfile_platform(sigfile_path, platform):
            log.debug(
                "Loading signature file", filepath=sigfile_path,
                platform=platform
            )
            if platform not in cls.platform_scanner:
                cls.platform_scanner[platform] = PatternScanner()

            try:
                cls.platform_scanner[platform].load_sigfile(sigfile_path)
            except (ValueError, TypeError, KeyError,
                    PatternSignatureError) as e:
                raise PluginError(
                    f"Failed to load signature file: {sigfile_path}. "
                    f"Error: {e}"
                ).with_traceback(e.__traceback__)

        # Read all pattern signature yml files and make a separate scanner
        # for each platform.
        patternsigs_dir = Paths.pattern_signatures()
        for platform in os.listdir(patternsigs_dir):
            platform_path = os.path.join(patternsigs_dir, platform)
            if not os.path.isdir(platform_path):
                continue

            for sigfile in os.listdir(platform_path):
                if not sigfile.endswith(".yml"):
                    continue

                add_sigfile_platform(
                    os.path.join(platform_path, sigfile), platform
                )

        # Ask each created scanner to compile patterns of each signature
        # into a hyperscan database.
        for platform, scanner in cls.platform_scanner.items():
            try:
                scanner.compile()
            except PatternSignatureError as e:
                raise PluginError(
                    f"Failed to compile signatures for platform: {platform}. "
                    f"Invalid Hyperscan regex in database. "
                    f"Hyperscan error: {e}"
                )

    def init(self):
        platform = self.taskctx.task.platform
        self.scanner = self.platform_scanner.get(platform)
        if not self.scanner:
            self.taskctx.log.warning(
                "No event pattern scanner for platform available",
                platform=platform
            )
            return

        self.match_tracker = self.scanner.new_tracker()

    def use_event(self, event):
        if not self.scanner:
            return

        event.pattern_scan(self.scanner)

    def finalize(self):
        if not self.match_tracker:
            return

        matched_patternsigs = self.match_tracker.get_matches()
        for match in matched_patternsigs:

            iocs = []
            for matchctx in match.get_iocs():
                process = self.taskctx.process_tracker.lookup_process(
                    matchctx.event.procid
                )

                duplicate = False
                # Find if the same value performed by the same process has
                # already been added to prevent a huge list of duplicate IOCs.
                for ioc in iocs:
                    if ioc["value"] != matchctx.orig_str:
                        continue

                    if ioc["process_id"] != matchctx.event.procid:
                        continue

                    duplicate = True

                if duplicate:
                    continue

                iocs.append({
                    "description": matchctx.event.description,
                    "value": matchctx.orig_str,
                    "process": "" if process is None else process.process_name,
                    "process_id": matchctx.event.procid
                })

            self.taskctx.signature_tracker.add_signature(
                name=match.name, short_description=match.short_description,
                description=match.description, score=match.score, iocs=iocs,
                family=match.family, tags=match.tags, ttps=match.ttps
            )

    def cleanup(self):
        for scanner in self.platform_scanner.values():
            scanner.clear()
