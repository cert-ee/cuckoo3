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

        cls.query_limit = cfg(
            "intelmq.yaml", "processing", "query_limit", subpkg="processing"
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

    def _search_ips(self, query_limit=10):
        network = self.ctx.result.get("network", {})
        queries = 0
        events = []
        for ip in network.get("host", []):
            if query_limit is not None and queries >= query_limit:
                break

            queries += 1
            events.extend(self.intelmq.find_ip(ip))

        return events

    def _search_domains(self, query_limit=10):
        network = self.ctx.result.get("network", {})
        queries = 0
        events = []
        for domain in network.get("domain", []):
            if query_limit is not None and queries >= query_limit:
                break

            queries += 1
            events.extend(self.intelmq.find_domain(domain))

        return events

    def _search_urls(self, query_limit=10):
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
            events.extend(self.intelmq.find_url(url))

        return events

    def start(self):
        events = []
        try:
            events.extend(self._search_ips(self.query_limit))
            events.extend(self._search_domains(self.query_limit))
            events.extend(self._search_urls(self.query_limit))
        except IntelMQError as e:
            self.ctx.log.warning("Failed to retrieve IntelMQ events", error=e)
            return

        return events
