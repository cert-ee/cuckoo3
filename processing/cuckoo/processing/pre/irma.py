# Copyright (C) 2019-2023 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import logging
import time
from urllib.parse import urlparse, urljoin
import requests
import json
import os

from cuckoo.common.config import cfg
from cuckoo.common.storage import Paths, Binaries

from ..abtracts import Processor
from ..signatures.signature import Scores, IOC

IRMA_FINISHED_STATUS = 50
irma_status = {
    0: "empty",
    10: "ready",
    20: "uploaded",
    30: "launched",
    40: "processed",
    50: "finished",
    60: "flushed",
    100: "cancelling",
    110: "cancelled",
    1000: "error",
    1010: "probelist missing",
    1011: "probe(s) not available",
    1020: "ftp upload error"
}


class Irma(Processor):

    CATEGORY = ["file"]
    KEY = "irma"

    @classmethod
    def enabled(cls):
        return cfg("irma", "enabled", subpkg="processing")

    def init(self):
        self.url = cfg(
            "irma", "url", subpkg="processing"
        )
        self.timeout = cfg(
            "irma", "timeout", subpkg="processing"
        )
        self.scan = cfg(
            "irma", "scan", subpkg="processing"
        )

        self.force = cfg(
            "irma", "force", subpkg="processing"
        )
        self.submitter = cfg(
            "irma", "submitter", subpkg="processing"
        )
        self.rescan_time = cfg(
            "irma", "rescan_time", subpkg="processing"
        )
        self.probes = cfg(
            "irma", "probes", subpkg="processing"
        )
        self.min_suspicious = cfg(
            "irma", "min_suspicious", subpkg="processing"
        )
        self.min_malicious = cfg(
            "irma", "min_malicious", subpkg="processing"
        )

    def wait_scan_finished(self,scan_id, pause=3, verbose=False):
        start = time.time()
        while True:
            if start + self.timeout < time.time():
                break
            results = self.get_scan_status(scan_id)
            status = results['status']
            status_name = irma_status[status]
            if verbose:
                self.ctx.log.debug(status_name)
            if status_name == 'finished':
                break
            elif status_name in ['flushed', 'cancelling', 'cancelled'] or status >= 1000: # >=1000 is for errors
                self.ctx.log.debug(f"Invalid scan state: {status_name}")
            time.sleep(pause)
        return results

    # get current scan data
    def get_scan_status(self,scan_id):
        return self._request_json(urljoin(self.url, f"/api/v2/scans/{scan_id}"))

    def _request_json(self, url, **kwargs):
        """Wrapper around doing a request and parsing its JSON output."""
        try:
            r = requests.get(url, timeout=self.timeout, **kwargs)
            return r.json() if r.status_code == 200 else {}
        except (requests.ConnectionError, ValueError) as e:
            self.ctx.log.error(
                f"Unable to fetch IRMA results: {e.message}"
            )
            return {}

    def _post_json(self, url, **kwargs):
        """Wrapper around doing a post and parsing its JSON output."""
        try:
            r = requests.post(url, timeout=self.timeout, **kwargs)
            if r.status_code == 200:
                return r.json()
            else:
                self.ctx.log.error(
                    f"IRMA request fail with status_code: {r.status_code}"
                )
                return {}
        except (requests.ConnectionError, ValueError) as e:
            self.ctx.log.error(
                f"Unable to fetch IRMA results: {e.message}"
            )
            return {}

    def _scan_file(self, filepath, force):
        # Initialize scan in IRMA.
        json_data = {'submitter': self.submitter}
        filename = os.path.basename(filepath)

        self.ctx.log.debug(
            f"Scanning file: {filepath}"
        )
        # Post file for scanning.
        with open(filepath, 'rb') as fd:
            submission_data = fd.read()
        files = {
            "files": (filename, submission_data, 'application/octet-stream'),
            "json": (None, json.dumps(json_data), 'application/json')
        }
        url = urljoin(self.url, "/api/v2/files_ext")
        file_id = self._post_json(url, files=files,).get('result_id',None)

        if not file_id:
            return None

        # launch posted file scan
        data = {'files': [file_id], 'options': {'force': force}}
        if self.probes:
            probes = self.probes.split(',')
            data['options']['probes'] = probes
        url = urljoin(self.url, "/api/v2/scans")
        scan_id = self._post_json(url, json=data,).get('id',None)

        if not scan_id:
            return None

        self.ctx.log.debug(f"Polling for results for ID {scan_id}")
        # poll scan status, waiting for it to finish
        finished_scan = self.wait_scan_finished(scan_id)

        results_id = finished_scan['results'][0]['result_id']
        return results_id

    def _get_results(self, sha256):
        # Fetch list of scan IDs.
        results = self._request_json(urljoin(self.url, f"/api/v2/files/{sha256}"))

        if not results.get("items"):
            self.ctx.log.debug(f"File {sha256} hasn't been scanned before")
            return None, None

        result_id = results.get("items")[-1]["result_id"]
        if result_id:
            results = self._request_json(urljoin(self.url, f"/api/v2/results/{result_id}"))
            timestamp_last_scan = results.get("file_infos").get("timestamp_last_scan")
        else:
            return None, None

        return r, timestamp_last_scan


    def _get_resultsbyid(self, result_id):
        # Fetch list of result ID.
        return self._request_json(urljoin(self.url, "/api/v2/results/{result_id}"))


    def _handle_file_target(self):
        try:
            target = self.ctx.result.get("target")
            results = self._request_json(urljoin(self.url, f"/api/v2/files/{target.sha256}"))

            if not self.force and not self.scan and not results:
                return None
            elif self.force or (not results and self.scan):
                if results.get("items") and self.rescan_time > 0:
                    result_id = results["items"][-1]["result_id"]
                    results = self._request_json(urljoin(self.url, f"/api/v2/results/{result_id}"))
                    timestamp_last_scan = results.get("file_infos").get("timestamp_last_scan")
                    now = time.time()
                    timediff_min = (now - timestamp_last_scan)/60
                    if timediff_min < self.rescan_time:
                        self.ctx.log.debug(
                            f"Last scan made {int(timediff_min)} minutes ago"
                        )
                        return results

                self.ctx.log.debug(
                    f"File scan requested: {target.sha256}"
                )
                file_path, _ = Binaries.path(Paths.binaries(), target.sha256)
                result_id = self._scan_file(file_path, self.force)
                self.ctx.log.debug(
                    f"File result_id: {result_id}"
                )
                if result_id:
                    results = self._get_resultsbyid(result_id) or {}

            if not results:
                return None
            if not results.get("probe_results",None):
                return None
        except Exception as e:
            self.ctx.log.warning(
                f"Error while making IRMA request: {e}"
            )
        return results

    def start(self):
        info = None
        if self.ctx.analysis.category == "file":
            info = self._handle_file_target()

        if not info:
            return {}

        if info.get("probe_results"):
            probe_avinfo = info.get("probe_results").get("antivirus")
        else:
            print(str(info))
            return {}
        malicious_count = len([r.get("results") for e,r in probe_avinfo.items() if r.get("results")])

        score = 0
        if malicious_count >= self.min_malicious:
            score = Scores.KNOWN_BAD
        elif malicious_count >= self.min_suspicious:
            # Suspicious. Decide what scores to use Cuckoo-wide and document.
            score = Scores.SUSPICIOUS

        if score:
            iocs = [
                IOC(antivirus=avname, result=avinfo.get("results"))
                for avname, avinfo in probe_avinfo.items()
                if avinfo.get("results")
            ]

            self.ctx.signature_tracker.add_signature(
                name="irma",
                score=score,
                short_description="IRMA sources report this target as "
                                  "malicious",
                description=f"{malicious_count} IRMA antivirus engines "
                            f"detect this target as malicious",
                iocs=iocs
            )

        return info
