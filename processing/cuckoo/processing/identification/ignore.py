# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from ..abtracts import Processor


class Ignore(Processor):

    KEY = "ignored"
    CATEGORY = ["file"]

    EXTS = (".jpg", ".png")
    SHA256 = [""]
    # 81de431987304676134138705fc1c21188ad7f27edf6b77a6551aa693194485e

    def start(self):
        matchers = [self.match_exts, self.match_sha256]
        ignored = []

        selection = self.results.get("identify", {}).get("selection", [])
        for f in selection[:]:
            for matcher in matchers:
                match, reason = matcher(f)
                if match:
                    ignored.append({
                        "filename": f.filename,
                        "filetype": f.magic,
                        "sha256": f.sha256,
                        "reason": reason
                    })

                    f.unselectable()
                    selection.remove(f)

        return ignored

    def match_sha256(self, f):
        if f.sha256 in self.SHA256:
            return True, "Safelisted sha256 hash"

        return False, None

    def match_exts(self, f):
        if f.filename.lower().endswith(self.EXTS):
            return True, "Safelisted extension"

        return False, None
