# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from ..abtracts import Reporter

from cuckoo.common.strictcontainer import Identification, Pre

class JSONDump(Reporter):

    ORDER = 1

    def report_identification(self):
        dump_path = os.path.join(self.analysis_path, "identification.json")
        ident = self.results.get("identify", {})
        submitted = ident.get("submitted", {})

        info = {
            "category": self.analysis.category,
            "selected": False
        }

        if self.errtracker.has_fatal():
            Identification(**info).to_file(dump_path)
            return

        # No file selection happens if the target category is URL. We can
        # dump the identification.json immediately.
        if self.analysis.category == "url":
            info.update({
                "selected": True,
                "target": submitted
            })
            Identification(**info).to_file(dump_path)
            return

        target = self.results.get("selected", {}).get("target", {})
        selected = self.results.get("selected", {}).get("selected")
        info.update({
            "selected": selected,
            "target": target,
            "ignored": self.results.get("ignored")
        })

        Identification(**info).to_file(dump_path)

    def report_pre_analysis(self):
        dump_path = os.path.join(self.analysis_path, "pre.json")
        Pre(
            target=self.results.get("target", {}),
            category=self.analysis.category
        ).to_file(dump_path)
