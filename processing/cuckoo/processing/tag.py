# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.


class TagTracker:
    def __init__(self):
        self._tags = set()

    @property
    def tags(self):
        return list(self._tags)

    def add_tag(self, tag):
        self._tags.add(tag)
