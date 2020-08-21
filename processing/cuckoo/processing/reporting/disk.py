# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from ..abtracts import Reporter

from cuckoo.common.strictcontainer import Identification, Pre
from cuckoo.common.storage import AnalysisPaths

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
                "target": submitted
            })
            Identification(**info).to_file(dump_path)
            return

        target = self.ctx.result.get("selected", {}).get("target", {})
        selected = self.ctx.result.get("selected", {}).get("selected")
        info.update({
            "selected": selected,
            "target": target,
            "ignored": self.ctx.result.get("ignored")
        })

        Identification(**info).to_file(dump_path)

    def report_pre_analysis(self):
        Pre(
            target=self.ctx.result.get("target", {}),
            category=self.ctx.analysis.category
        ).to_file(AnalysisPaths.prejson(self.ctx.analysis.id))
