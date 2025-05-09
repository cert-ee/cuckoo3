# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.misp import MispClient, MispError
from cuckoo.common.config import cfg

from ..abtracts import Processor
from ..errors import DisablePluginError


class MISPInfoGather(Processor):
    CATEGORY = ["file", "url"]
    KEY = "misp"

    hashes = []

    @classmethod
    def enabled(cls):
        return cfg("misp.yaml", "processing", "enabled", subpkg="processing")

    @classmethod
    def init_once(cls):
        cls.hashes = cfg(
            "misp", "processing", "pre", "file", "hashes", subpkg="processing"
        )
        cls.url = cfg("misp", "processing", "url", subpkg="processing")
        cls.verify_tls = cfg("misp", "processing", "verify_tls", subpkg="processing")
        cls.key = cfg("misp", "processing", "key", subpkg="processing")
        cls.conn_timeout = cfg("misp", "processing", "timeout", subpkg="processing")
        cls.event_limit = cfg(
            "misp", "processing", "pre", "event_limit", subpkg="processing"
        )
        cls.to_ids = cfg(
            "misp", "processing", "pre", "query_ids_flag", subpkg="processing"
        )
        cls.publish_timestamp = cfg(
            "misp", "processing", "pre", "publish_timestamp", subpkg="processing"
        )

    def init(self):
        try:
            self.misp_client = MispClient(
                misp_url=self.url,
                api_key=self.key,
                timeout=self.conn_timeout,
                verify_tls=self.verify_tls,
            )
        except MispError as e:
            raise DisablePluginError(f"Failed to connect to MISP server. Error: {e}")

    def _search_events_hashes(self, target):
        hash_lookup = {
            "md5": self.misp_client.find_file_md5,
            "sha1": self.misp_client.find_file_sha1,
            "sha256": self.misp_client.find_file_sha256,
            "sha512": self.misp_client.find_file_sha512,
        }

        events = []
        for hashalgo in self.hashes:
            lookup_handler = hash_lookup.get(hashalgo)
            if not lookup_handler:
                continue

            events.extend(
                lookup_handler(
                    target[hashalgo],
                    limit=self.event_limit,
                    to_ids=self.to_ids,
                    publish_timestamp=self.publish_timestamp,
                )
            )

        return events

    def start(self):
        target = self.ctx.result.get("target")
        events = []
        try:
            if self.ctx.analysis.category == "url":
                events = self.misp_client.find_url(
                    target.target,
                    limit=self.event_limit,
                    to_ids=self.to_ids,
                    publish_timestamp=self.publish_timestamp,
                )
            elif self.ctx.analysis.category == "file":
                events = self._search_events_hashes(target)
        except MispError as e:
            self.ctx.log.warning("Failed to retrieve MISP events", error=e)
            return []

        return [event.to_dict() for event in events]
