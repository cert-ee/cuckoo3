# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.config import cfg
from cuckoo.common import virustotal

from ..abtracts import Processor
from ..signatures.signature import Scores, IOC


class Virustotal(Processor):
    CATEGORY = ["file", "url"]
    KEY = "virustotal"

    @classmethod
    def enabled(cls):
        return cfg("virustotal", "enabled", subpkg="processing")

    @classmethod
    def init_once(cls):
        virustotal.set_api_key(cfg("virustotal", "key", subpkg="processing"))

    def init(self):
        self.min_suspicious = cfg("virustotal", "min_suspicious", subpkg="processing")
        self.min_malicious = cfg("virustotal", "min_malicious", subpkg="processing")

    def _handle_file_target(self):
        try:
            return virustotal.fileinfo_request(self.ctx.result.get("target").sha256)
        except virustotal.VirustotalError as e:
            self.ctx.log.warning("Error while making Virustotal request", error=e)

        return None

    def _handle_url_target(self):
        try:
            return virustotal.urlinfo_request(self.ctx.result.get("target").url)
        except virustotal.VirustotalError as e:
            self.ctx.log.warning("Error while making Virustotal request", error=e)

        return None

    def start(self):
        info = None
        if self.ctx.analysis.category == "file":
            info = self._handle_file_target()
        elif self.ctx.analysis.category == "url":
            info = self._handle_url_target()

        if not info:
            return {}

        malicious_count = info["stats"]["malicious"]

        score = 0
        if malicious_count >= self.min_malicious:
            score = Scores.KNOWN_BAD
        elif malicious_count >= self.min_suspicious:
            # Suspicious. Decide what scores to use Cuckoo-wide and document.
            score = Scores.SUSPICIOUS

        if score:
            iocs = [
                IOC(antivirus=avname)
                for avname, avinfo in info["avs"].items()
                if avinfo["category"] == "malicious"
            ]

            self.ctx.signature_tracker.add_signature(
                name="virustotal",
                score=score,
                short_description="Virustotal sources report this target as malicious",
                description=f"{malicious_count} Virustotal antivirus engines "
                f"detect this target as malicious",
                iocs=iocs,
            )

        return info
