# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.
import logging

from cuckoo.common.config import cfg
from cuckoo.common.misp import MispClient, MispError, NewMispEvent
from cuckoo.common.storage import Binaries, Paths, AnalysisPaths
from cuckoo.common.strictcontainer import Pre
from cuckoo.common.safelist import IPMisp, DomainMisp, URLMisp

from ..abtracts import Reporter
from ..errors import DisablePluginError
from ..signatures.signature import Signature

logging.getLogger("pymisp").setLevel(logging.WARNING)

class MISP(Reporter):

    @classmethod
    def enabled(cls):
        return cfg("misp", "reporting", "enabled", subpkg="processing")

    @classmethod
    def init_once(cls):
        cls.url = cfg("misp", "url", subpkg="processing")
        cls.verify_tls = cfg("misp", "verify_tls", subpkg="processing")
        cls.key = cfg("misp", "key", subpkg="processing")
        cls.conn_timeout = cfg("misp", "timeout", subpkg="processing")
        cls.min_score = cfg(
            "misp", "reporting", "min_score", subpkg="processing"
        )
        cls.web_baseurl = cfg(
            "misp", "reporting", "web_baseurl", subpkg="processing"
        )
        cls.event_settings = cfg(
            "misp", "reporting", "event", subpkg="processing"
        )
        cls.attributes = cfg(
            "misp", "reporting", "event", "attributes", subpkg="processing"
        )

        cls.domain_sl = DomainMisp()
        cls.domain_sl.load_safelist()
        cls.ip_sl = IPMisp()
        cls.ip_sl.load_safelist()
        cls.url_sl = URLMisp()
        cls.url_sl.load_safelist()

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

    def _add_signatures(self, event):
        # Add behavioral signatures
        for signature in self.ctx.signature_tracker.signatures:
            event.add_signature(
                name=signature.name, description=signature.description
            )

        # Add signatures from pre phase. Do it here because we want all
        # attributes in one MISP event, without overcomplicating the
        # creation process.
        pre = Pre.from_file(AnalysisPaths.prejson(self.ctx.analysis.id))
        for sigdict in pre.signatures:
            sig = Signature.from_dict(sigdict)
            event.add_signature(name=sig.name, description=sig.description)

    def _add_mitre_attack_ttps(self, event):
        for ttp in self.ctx.ttp_tracker.ttps:
            event.add_mitre_attack(ttp)

    def _add_ips(self, event):
        network = self.ctx.result.get("network", {})

        for ip in network.get("host", []):
            if self.ip_sl.is_safelisted(ip, self.ctx.machine.platform):
                continue

            event.add_ip(
                ip, intrusion_detection=self.attributes["ip_addresses"]["ids"]
            )

    def _add_domains(self, event):
        network = self.ctx.result.get("network", {})

        for domain in network.get("domain", []):
            if self.domain_sl.is_safelisted(domain, self.ctx.machine.platform):
                continue

            event.add_domain(
                domain, intrusion_detection=self.attributes["domains"]["ids"]
            )

    def _add_urls(self, event):
        network = self.ctx.result.get("network", {})

        for http in network.get("http", []):
            url = http.get("request", {}).get("url")
            if not url:
                continue

            if self.url_sl.is_safelisted(url, self.ctx.machine.platform):
                continue

            event.add_url(
                url, intrusion_detection=self.attributes["urls"]["ids"]
            )

    def _add_mutexes(self, event):
        pass

    def _add_sample(self, event):
        target = self.ctx.analysis.target
        filepath = None
        if self.attributes["sample_hashes"]["upload_sample"]:
            filepath, _ = Binaries.path(Paths.binaries(), target.sha256)

        event.add_file(
            filename=target.filename, md5=target.md5, sha1=target.sha1,
            sha256=target.sha256, size=target.size,
            media_type=target.media_type, filepath=filepath,
            intrusion_detection=self.attributes["sample_hashes"]["ids"],
            comment="Submitted file"
        )

    def report_post_analysis(self):
        if self.ctx.signature_tracker.score < self.min_score:
            return

        event = NewMispEvent(
            info=f"Cuckoo Sandbox task {self.ctx.task.id}",
            distribution=self.event_settings["distribution"],
            analysis=self.event_settings["analysis"],
            sharing_group=self.event_settings["sharing_group"],
            threat_level=self.event_settings["threat_level"],
            tags=self.event_settings["tags"]
        )

        event.add_task_info(
            analysis_id=self.ctx.analysis.id, task_id=self.ctx.task.id,
            webinterface_baseurl=self.web_baseurl
        )
        self._add_signatures(event)

        if self.event_settings["galaxy_mitre_attack"]:
            self._add_mitre_attack_ttps(event)

        if self.attributes["ip_addresses"]["include"]:
            self._add_ips(event)

        if self.attributes["domains"]["include"]:
            self._add_domains(event)

        if self.attributes["urls"]["include"]:
            self._add_urls(event)

        if self.attributes["mutexes"]["include"]:
            self._add_mutexes(event)

        if self.ctx.analysis.category == "file":
            if self.attributes["sample_hashes"]["include"]:
                self._add_sample(event)

        if self.event_settings["publish"]:
            event.set_published()

        try:
            self.misp_client.create_event(event)
        except MispError as e:
            self.ctx.log.warning(f"Submission of MISP event failed: {e}")
