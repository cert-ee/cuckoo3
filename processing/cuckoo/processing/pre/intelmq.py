# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common.intelmq import IntelMQElastic, IntelMQError
from cuckoo.common.config import cfg

from ..abtracts import Processor
from ..errors import DisablePluginError

class IntelMQInfoGather(Processor):

    CATEGORY = ["file", "url"]
    KEY = "intelmq"

    @classmethod
    def enabled(cls):
        return cfg(
            "intelmq.yaml", "processing", "enabled", subpkg="processing"
        )

    @classmethod
    def init_once(cls):
        hosts = cfg("intelmq.yaml", "processing", "hosts", subpkg="processing")
        index_name = cfg(
            "intelmq.yaml", "processing", "index_name", subpkg="processing"
        )
        limit = cfg(
            "intelmq.yaml", "processing", "event_limit",
            subpkg="processing"
        )
        link_url = cfg(
            "intelmq.yaml", "processing", "link_url", subpkg="processing"
        )

        cls.intelmq = IntelMQElastic(
            elastic_hosts=hosts, index_name=index_name, event_limit=limit,
            link_url=link_url
        )

    def init(self):
        try:
            self.intelmq.verify()
        except IntelMQError as e:
            raise DisablePluginError(
                f"IntelMQ Elasticsearch verification failed: {e}"
            )

    def _search_events_hashes(self, target):
        hash_lookupmethod = {
            target.md5: self.intelmq.find_file_md5,
            target.sha1: self.intelmq.find_file_sha1,
            target.sha256: self.intelmq.find_file_sha256
        }

        for hash, lookupmethod in hash_lookupmethod.items():
            events = lookupmethod(hash)
            if events:
                return events

    def start(self):
        target = self.ctx.result.get("target")
        events = []
        try:
            if self.ctx.analysis.category == "url":
                events = self.intelmq.find_url(target.url)
            elif self.ctx.analysis.category == "file":
                events = self._search_events_hashes(target)
        except IntelMQError as e:
            self.ctx.log.warning("Failed to retrieve IntelMQ events", error=e)
            return []

        return events


# TODO woe
# config processing intelmq afmaken
# config reporting moet iets van een accuracy veld of een vrije
# dict bij die opgestuurd wordt met elk event. <--
# pre en post module + disk json dump toevoegen
# misp reporting maken. Kan zonder account.
# testen als account er is.

