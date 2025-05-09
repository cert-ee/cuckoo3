# Copyright (C) 2019-2023 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import logging
import time
from urllib.parse import urljoin
import requests
from requests.auth import HTTPBasicAuth
import json

from cuckoo.common.config import cfg

from ..abtracts import Processor
from ..signatures.signature import Scores, IOC


class MHRInfoGather(Processor):
    CATEGORY = ["file"]
    KEY = "mhr"

    @classmethod
    def enabled(cls):
        return cfg("mhr", "enabled", subpkg="processing")

    def init(self):
        self.url = cfg("mhr", "url", subpkg="processing")
        self.timeout = cfg("mhr", "timeout", subpkg="processing")
        self.user = cfg("mhr", "user", subpkg="processing")
        self.password = cfg("mhr", "password", subpkg="processing")
        self.min_suspicious = cfg("mhr", "min_suspicious", subpkg="processing")
        self.min_malicious = cfg("mhr", "min_malicious", subpkg="processing")

    def _get_results(self, sha256):
        results = self._request_json(urljoin(self.url, sha256))

        if results:
            return results
        else:
            return None

    def _request_json(self, url, **kwargs):
        """Wrapper around doing a request and parsing its JSON output."""
        try:
            r = requests.get(
                url,
                auth=HTTPBasicAuth(self.user, self.password),
                timeout=self.timeout,
                verify=False,
                **kwargs,
            )
            return r.json() if r.status_code == 200 else {}
        except (requests.ConnectionError, ValueError) as e:
            self.ctx.log.error(f"Unable to fetch MHR results: {e}")
            return {}

    def _handle_file_target(self):
        info = None
        try:
            target = self.ctx.result.get("target")
            info = self._get_results(target.sha256)

            if not info:
                return None
        except Exception as e:
            self.ctx.log.warning(f"Error while making MHR request: {e}")
        return info

    def start(self):
        antivirus_detection_rate = None
        if self.ctx.analysis.category == "file":
            info = self._handle_file_target()

        if not info:
            return {}

        score = 0
        if info["antivirus_detection_rate"]:
            if info["antivirus_detection_rate"] >= self.min_malicious:
                score = Scores.KNOWN_BAD
            elif info["antivirus_detection_rate"] >= self.min_suspicious:
                # Suspicious. Decide what scores to use Cuckoo-wide and document.
                score = Scores.SUSPICIOUS
        else:
            return {}
        if score:
            iocs = [IOC(antivirus="MHR", result=info["antivirus_detection_rate"])]

            self.ctx.signature_tracker.add_signature(
                name="mhr",
                score=score,
                short_description="MHR sources report this target as malicious",
                description=f"{info['antivirus_detection_rate']} percentage of tested MHR antivirus engines"
                f"detect this target as malicious",
                iocs=iocs,
            )

        return info
