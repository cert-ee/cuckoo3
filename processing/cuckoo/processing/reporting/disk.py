# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from ..abtracts import Reporter

from cuckoo.common.strictcontainer import Identification, Pre, Post
from cuckoo.common.storage import AnalysisPaths, TaskPaths

class JSONDump(Reporter):

    ORDER = 1

    def report_identification(self):
        dump_path = AnalysisPaths.identjson(self.ctx.analysis.id)
        ident = self.ctx.result.get("identify", {})
        submitted = ident.get("submitted", {})

        info = {
            "category": self.ctx.analysis.category,
            "selected": False
        }

        # No file selection happens if the target category is URL. We can
        # dump the identification.json immediately.
        if self.ctx.analysis.category == "url":
            info.update({
                "selected": True,
                "identified": True,
                "target": submitted
            })
            Identification(**info).to_file(dump_path)
            return

        target = self.ctx.result.get("selected", {}).get("target", {})
        selected = self.ctx.result.get("selected", {}).get("selected")
        identified = self.ctx.result.get("selected", {}).get("identified")
        info.update({
            "selected": selected,
            "identified": identified,
            "target": target,
            "ignored": self.ctx.result.get("ignored")
        })

        Identification(**info).to_file(dump_path)

    def report_pre_analysis(self):
        include_result = ["virustotal", "static"]
        static = {
            "analysis_id": self.ctx.analysis.id,
            "score": self.ctx.signature_tracker.score,
            "signatures": self.ctx.signature_tracker.signatures_to_dict(),
            "target": self.ctx.result.get("target", {}),
            "category": self.ctx.analysis.category
        }

        for resultkey in include_result:
            if resultkey in self.ctx.result:
                static[resultkey] = self.ctx.result.get(resultkey)

        Pre(**static).to_file(AnalysisPaths.prejson(self.ctx.analysis.id))

    def report_post_analysis(self):
        Post(**{
            "task_id": self.ctx.task.id,
            "score": self.ctx.signature_tracker.score,
            "signatures": self.ctx.signature_tracker.signatures_to_dict(),
            "ttps": self.ctx.ttp_tracker.ttps,
            "tags": self.ctx.tag_tracker.tags
        }).to_file(TaskPaths.report(self.ctx.task.id))
