# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from ..abtracts import Reporter

from cuckoo.common.config import cfg
from cuckoo.common.strictcontainer import Identification, Pre, Post
from cuckoo.common.storage import AnalysisPaths, TaskPaths


class JSONDump(Reporter):
    ORDER = 1

    def init(self):
        self.max_processes = cfg(
            "post.yaml", "processes", "max_processes", subpkg="processing"
        )
        self.max_iocs = cfg("post.yaml", "signatures", "max_iocs", subpkg="processing")
        self.max_ioc_size = cfg(
            "post.yaml", "signatures", "max_ioc_bytes", subpkg="processing"
        )

    def report_identification(self):
        selected = self.ctx.result.get("selected", {})
        info = {
            "category": self.ctx.analysis.category,
            "selected": selected.get("selected"),
            "identified": selected.get("identified"),
            "target": selected.get("target", {}),
            "ignored": self.ctx.result.get("ignored", []),
        }
        Identification(**info).to_file(AnalysisPaths.identjson(self.ctx.analysis.id))

    def report_pre_analysis(self):
        include_result = [
            "virustotal",
            "irma",
            "mhr",
            "static",
            "misp",
            "intelmq",
            "command",
            "snort",
        ]

        # Pre might change settings such as launch args for specific chosen
        # browser. In this case, the platforms list is changed. This means
        # it must be updated/overwritten in analysis.json. We tell the
        # state control component this by adding the platforms list to the
        # pre report.
        if self.ctx.analysis.settings.was_updated:
            platforms = self.ctx.analysis.settings.platforms
        else:
            platforms = []

        static = {
            "analysis_id": self.ctx.analysis.id,
            "score": self.ctx.signature_tracker.score,
            "signatures": self.ctx.signature_tracker.signatures_to_dict(),
            "target": self.ctx.result.get("target", {}),
            "category": self.ctx.analysis.category,
            "ttps": self.ctx.ttp_tracker.to_dict(),
            "tags": self.ctx.tag_tracker.tags,
            "families": self.ctx.family_tracker.families,
            "platforms": platforms,
        }

        for resultkey in include_result:
            if resultkey in self.ctx.result:
                static[resultkey] = self.ctx.result.get(resultkey)

        Pre(**static).to_file(AnalysisPaths.prejson(self.ctx.analysis.id))

    def report_post_analysis(self):
        include_result = [
            "misp",
            "network",
            "cfgextr",
            "intelmq",
            "screenshot",
            "suricata",
        ]

        post_report = {
            "task_id": self.ctx.task.id,
            "score": self.ctx.signature_tracker.score,
            "signatures": self.ctx.signature_tracker.signatures_to_dict(
                max_iocs=self.max_iocs, max_ioc_size=self.max_ioc_size
            ),
            "ttps": self.ctx.ttp_tracker.to_dict(),
            "tags": self.ctx.tag_tracker.tags,
            "families": self.ctx.family_tracker.families,
            "processes": self.ctx.process_tracker.to_dict(
                max_processes=self.max_processes
            ),
        }

        for resultkey in include_result:
            if resultkey in self.ctx.result:
                post_report[resultkey] = self.ctx.result.get(resultkey)

        Post(**post_report).to_file(TaskPaths.report(self.ctx.task.id))


class TLSMasterSecrets(Reporter):
    def report_post_analysis(self):
        if not self.ctx.network.tls.sessions:
            return

        # Write format:
        # CLIENT_RANDOM <hex client random bytes> <hex secret bytes>
        with open(TaskPaths.tlsmaster(self.ctx.task.id), "w") as fp:
            for randoms, secret in self.ctx.network.tls.sessions.items():
                fp.write(f"CLIENT_RANDOM {randoms[0].hex()} {secret.hex()}\n")
