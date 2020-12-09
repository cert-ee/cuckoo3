# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class TTPTracker:

    def __init__(self):
        self._ttps = set()

    @property
    def ttps(self):
        return list(self._ttps)

    def add_ttp(self, ttp):
        self._ttps.add(ttp)
