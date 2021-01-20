# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.


class Levels:
    INFORMATIONAL = "informational"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


class Scores:
    NOTHING_DETECTED = 1
    SUSPICIOUS = 6
    LIKELY_MALICIOUS = 8
    MALICIOUS = 9
    KNOWN_BAD = 10

class Signature:

    def __init__(self, score, name, short_description, description="", iocs=[],
                 ttps=[], tags=[], family=""):
        self.name = name
        self.short_description = short_description

        if not description:
            self.description = short_description
        else:
            self.description = description

        self.ttps = ttps
        self.tags = tags
        self.family = family
        self.iocs = iocs

        if family:
            self.score = Scores.KNOWN_BAD
        else:
            self.score = score

    def add_iocs(self, iocs=[]):
        self.iocs.extend(iocs)

    @classmethod
    def from_dict(cls, sigdict):
        return cls(
            score=sigdict["score"], name=sigdict["name"],
            short_description=sigdict["short_description"],
            description=sigdict["description"], iocs=sigdict["iocs"],
            ttps=sigdict["ttps"], tags=sigdict["tags"],
            family=sigdict["family"]
        )

    def to_dict(self):
        return {
            "name": self.name,
            "short_description": self.short_description,
            "description": self.description,
            "ttps": self.ttps,
            "tags": self.tags,
            "family": self.family,
            "iocs": self.iocs,
            "score": self.score
        }

class SignatureTracker:

    def __init__(self, tagtracker, ttptracker):
        self._triggered_signatures = {}
        self._tag_tracker = tagtracker
        self._ttp_tracker = ttptracker
        self._families = set()

    @property
    def score(self):
        score = Scores.NOTHING_DETECTED
        for sig in self._triggered_signatures.values():
            if sig.score > score:
                score = sig.score

        return score

    @property
    def signatures(self):
        return [sig for sig in self._triggered_signatures.values()]

    def signatures_to_dict(self):
        return [sig.to_dict() for sig in self._triggered_signatures.values()]

    def _add_new_signature(self, score, name, short_description,
                           description="", iocs=[], ttps=[], tags=[],
                           family=""):
        for tag in tags:
            self._tag_tracker.add_tag(tag)

        for ttp in ttps:
            self._ttp_tracker.add_ttp(ttp)

        if family:
            self._families.add(family)

        self._triggered_signatures[name] = Signature(
            score=score, name=name, short_description=short_description,
            description=description, iocs=iocs, ttps=ttps, tags=tags,
            family=family
        )

    def add_signature(self, score, name, short_description, description="",
                      iocs=[], ttps=[], tags=[], family=""):

        signature = self._triggered_signatures.get(name)
        if not signature:
            self._add_new_signature(
                score=score, name=name, short_description=short_description,
                description=description, iocs=iocs, ttps=ttps, tags=tags,
                family=family
            )
        else:
            signature.add_iocs(iocs)
