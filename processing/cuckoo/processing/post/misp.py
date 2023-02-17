# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.misp import MispClient, MispError
from cuckoo.common.config import cfg

from ..abtracts import Processor
from ..errors import DisablePluginError

class MispInfoGather(Processor):

    CATEGORY = ["file", "url"]
    KEY = "misp"

    @classmethod
    def enabled(cls):
        return cfg("misp.yaml", "processing", "enabled", subpkg="processing")

    @classmethod
    def init_once(cls):
        cls.url = cfg("misp", "processing", "url", subpkg="processing")
        cls.verify_tls = cfg("misp", "processing", "verify_tls", subpkg="processing")
        cls.key = cfg("misp", "processing", "key", subpkg="processing")
        cls.conn_timeout = cfg("misp", "processing", "timeout", subpkg="processing")
        cls.query_limits = cfg(
            "misp", "processing", "post", "query_limits", subpkg="processing"
        )
        cls.event_limits = cfg(
            "misp", "processing", "post", "event_limits", subpkg="processing"
        )

    def init(self):
        try:
            self.misp_client = MispClient(
                misp_url=self.url, api_key=self.key, timeout=self.conn_timeout,
                verify_tls=self.verify_tls
            )
        except MispError as e:
            raise DisablePluginError(
                f"Failed to connect to MISP server. Error: {e}"
            )

    def _search_dst_ips(self, query_limit=None, event_limit=1):
        network = self.ctx.result.get("network", {})

        queries = 0
        events = []
        for ip in network.get("host", []):
            if query_limit is not None and queries >= query_limit:
                break

            queries += 1
            events.extend(self.misp_client.find_ip_dst(ip, limit=event_limit))

        return events

    def _search_domains(self, query_limit=None, event_limit=1):
        network = self.ctx.result.get("network", {})

        queries = 0
        events = []
        for domain in network.get("domain", []):
            if query_limit is not None and queries >= query_limit:
                break

            queries += 1
            events.extend(
                self.misp_client.find_domain(domain, limit=event_limit)
            )

        return events

    def _search_urls(self, query_limit=None, event_limit=1):
        network = self.ctx.result.get("network", {})

        queries = 0
        events = []
        for http in network.get("http", []):
            if query_limit is not None and queries >= query_limit:
                break

            url = http.get("request", {}).get("url")
            if not url:
                continue

            queries += 1
            events.extend(self.misp_client.find_url(url, limit=event_limit))

        return events

    # TODO support this when we have dropped files.
    def _search_dropped_files(self, query_limit):
        pass

    def start(self):
        events = []
        try:
            events.extend(
                self._search_dst_ips(
                    query_limit=self.query_limits.get("dst_ip"),
                    event_limit=self.event_limits.get("dst_ip", 1)
                )
            )
            events.extend(
                self._search_urls(
                    query_limit=self.query_limits.get("url"),
                    event_limit=self.event_limits.get("url", 1)
                )
            )
            events.extend(
                self._search_domains(
                    query_limit=self.query_limits.get("domain"),
                    event_limit=self.event_limits.get("domain", 1)
                )
            )
        except MispError as e:
            self.ctx.log.warning("Failed to retrieve MISP events", error=e)
            return []

        return [event.to_dict() for event in events]
