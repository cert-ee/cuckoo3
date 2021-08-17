# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.config import cfg
from cuckoo.common.safelist import IPIntelMQ, DomainIntelMQ, URLIntelMQ
from cuckoo.common.intelmq import IntelMQEventMaker, IntelMQError

from ..abtracts import Reporter

class IntelMQ(Reporter):

    @classmethod
    def enabled(cls):
        return cfg("intelmq.yaml", "reporting", "enabled", subpkg="processing")

    @classmethod
    def init_once(cls):
        cls.api_url = cfg(
            "intelmq.yaml", "reporting", "api_url", subpkg="processing"
        )
        cls.verify_tls = cfg(
            "intelmq.yaml", "reporting", "verify_tls", subpkg="processing"
        )
        cls.min_score = cfg(
            "intelmq.yaml", "reporting", "min_score", subpkg="processing"
        )
        cls.web_baseurl = cfg(
            "intelmq.yaml", "reporting", "web_baseurl", subpkg="processing"
        )
        cls.feed_accuracy = cfg(
            "intelmq.yaml", "reporting", "feed_accuracy", subpkg="processing"
        )
        cls.event_desc = cfg(
            "intelmq.yaml", "reporting", "event_description",
            subpkg="processing"
        )

        cls.domain_sl = DomainIntelMQ()
        cls.domain_sl.load_safelist()
        cls.ip_sl = IPIntelMQ()
        cls.ip_sl.load_safelist()
        cls.url_sl = URLIntelMQ()
        cls.url_sl.load_safelist()

    def _add_ips(self, maker):
        network = self.ctx.result.get("network", {})
        for ip in network.get("host", []):
            if self.ip_sl.is_safelisted(ip, self.ctx.machine.platform):
                continue

            maker.add_dst_ip(ip)


    def _add_domains(self, maker):
        network = self.ctx.result.get("network", {})
        for domain in network.get("domain", []):
            if self.domain_sl.is_safelisted(domain, self.ctx.machine.platform):
                continue

            maker.add_dst_domain(domain)

    def _add_urls(self, maker):
        network = self.ctx.result.get("network", {})
        for http in network.get("http", []):
            url = http.get("request", {}).get("url")
            if not url:
                continue

            if self.url_sl.is_safelisted(url, self.ctx.machine.platform):
                continue

            maker.add_dst_url(url)

    def _add_file_target(self, maker):
        target = self.ctx.analysis.target
        families = self.ctx.family_tracker.families
        if families:
            maker.add_malware_file(
                target.md5, target.sha1, target.sha256, family=families[0]
            )
        else:
            maker.add_malware_file(
                target.md5, target.sha1, target.sha256
            )

    def report_post_analysis(self):
        maker = IntelMQEventMaker(
            self.ctx.analysis.id, self.ctx.task.id,
            webinterface_baseurl=self.web_baseurl,
            feed_accuracy=self.feed_accuracy, event_description=self.event_desc
        )

        self._add_ips(maker)
        self._add_domains(maker)
        self._add_urls(maker)
        if self.ctx.analysis.category == "file":
            self._add_file_target(maker)

        try:
            maker.submit(self.api_url, verify_tls=self.verify_tls)
        except IntelMQError as e:
            self.ctx.log.warning("IntelMQ events creation failed.", error=e)
