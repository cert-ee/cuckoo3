# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class TagTracker:

    def __init__(self):
        self._tags = set()

    @property
    def tags(self):
        return list(self._tags)

    def add_tag(self, tag):
        self._tags.add(tag)
