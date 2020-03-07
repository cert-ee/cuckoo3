# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os

from ..helpers import Reporter
from ..typehelpers import Identification

class JSONDump(Reporter):

    ORDER = 1

    def report_identification(self):
        dump_path = os.path.join(self.analysis_path, "identification.json")
        ident = self.results.get("identify", {})
        target = self.results.get("selected", {})
        submitted = ident.get("submitted", {})

        info = {
            "errors": self.errtracker.to_dict(),
            "category": self.analysis.category,
            "selected": False
        }

        if self.errtracker.state != self.errtracker.OK:
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

        if target:
            selected = True
        else:
            selected = False
            target = submitted

        # If the submitted file is a container and the current target is not
        # that most outer container. Set the hash of the submitted outer
        # parent so it can be easily found in other stages.
        parent = ""
        if submitted["container"] and target["sha256"] != submitted["sha256"]:
            parent = submitted["sha256"]

        # Byte decoding until the new Sflock is finished. TODO
        fname = target["filename"]
        if isinstance(fname, bytes):
            target["filename"] = fname.decode()

        # Platform must be a string
        target["platform"] = target["platform"] or ""

        info.update({
            "selected": selected,
            "target": target,
            "ignored": self.results.get("ignored"),
            "parent": parent
        })

        Identification(**info).to_file(dump_path)

    def report_pre_analysis(self):
        dump_path = os.path.join(self.analysis_path, "pre.json")
        with open(dump_path, "w") as fp:
            json.dump({"errors": self.errtracker.to_dict()}, fp, indent=1)
