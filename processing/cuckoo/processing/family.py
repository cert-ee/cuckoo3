# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class FamilyTracker:

    def __init__(self):
        self._families = set()

    @property
    def families(self):
        return list(self._families)

    def add_family(self, family):
        self._families.add(family)
