# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

class FamilyTracker:

    def __init__(self):
        self._families = set()

    @property
    def families(self):
        return list(self._families)

    def add_family(self, family):
        self._families.add(family)
