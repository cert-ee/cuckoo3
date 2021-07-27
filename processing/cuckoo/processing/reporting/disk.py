# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from ..abtracts import Reporter

from cuckoo.common.strictcontainer import Identification, Pre, Post
from cuckoo.common.storage import AnalysisPaths, TaskPaths

class JSONDump(Reporter):

    ORDER = 1

    def report_identification(self):
        selected = self.ctx.result.get("selected", {})
        info = {
            "category": self.ctx.analysis.category,
            "selected": selected.get("selected"),
            "identified": selected.get("identified"),
            "target": selected.get("target", {}),
            "ignored": self.ctx.result.get("ignored", [])
        }
        Identification(**info).to_file(
            AnalysisPaths.identjson(self.ctx.analysis.id)
        )

    def report_pre_analysis(self):
        include_result = [
            "virustotal", "static", "misp", "intelmq", "command"
        ]
        static = {
            "analysis_id": self.ctx.analysis.id,
            "score": self.ctx.signature_tracker.score,
            "signatures": self.ctx.signature_tracker.signatures_to_dict(),
            "target": self.ctx.result.get("target", {}),
            "category": self.ctx.analysis.category,
            "ttps": self.ctx.ttp_tracker.to_dict(),
            "tags": self.ctx.tag_tracker.tags,
            "families": self.ctx.family_tracker.families
        }

        for resultkey in include_result:
            if resultkey in self.ctx.result:
                static[resultkey] = self.ctx.result.get(resultkey)

        Pre(**static).to_file(AnalysisPaths.prejson(self.ctx.analysis.id))

    def report_post_analysis(self):
        include_result = [
            "misp", "network", "cfgextr", "intelmq", "screenshot"
        ]

        post_report = {
            "task_id": self.ctx.task.id,
            "score": self.ctx.signature_tracker.score,
            "signatures": self.ctx.signature_tracker.signatures_to_dict(),
            "ttps": self.ctx.ttp_tracker.to_dict(),
            "tags": self.ctx.tag_tracker.tags,
            "families": self.ctx.family_tracker.families,
            "processes": self.ctx.process_tracker.process_dictlist()
        }

        for resultkey in include_result:
            if resultkey in self.ctx.result:
                post_report[resultkey] = self.ctx.result.get(resultkey)

        Post(**post_report).to_file(TaskPaths.report(self.ctx.task.id))
