# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

class Scores:
    NOTHING_DETECTED = 0
    INFORMATIONAL = 1
    SUSPICIOUS = 6
    LIKELY_MALICIOUS = 8
    MALICIOUS = 9
    KNOWN_BAD = 10

class Levels:
    INFORMATIONAL = "informational"
    SUSPICIOUS = "suspicious"
    LIKELY_MALICIOUS = "likely malicious"
    MALICIOUS = "malicious"
    KNOWN_BAD = "known bad"

    LEVEL_SCORE = {
        INFORMATIONAL: Scores.INFORMATIONAL,
        SUSPICIOUS: Scores.SUSPICIOUS,
        LIKELY_MALICIOUS: Scores.LIKELY_MALICIOUS,
        MALICIOUS: Scores.MALICIOUS,
        KNOWN_BAD: Scores.KNOWN_BAD
    }

    @classmethod
    def to_score(cls, desc):
        score = cls.LEVEL_SCORE.get(desc.lower())
        if not score:
            raise KeyError(f"Unknown score level type: {desc}")

        return score

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
        self.iocs = set()

        if family:
            self.score = Scores.KNOWN_BAD
        else:
            self.score = score

        self.add_iocs(iocs)

    def add_iocs(self, iocs=[]):
        self.iocs.update(iocs)

    @classmethod
    def from_dict(cls, sigdict):
        return cls(
            score=sigdict["score"], name=sigdict["name"],
            short_description=sigdict["short_description"],
            description=sigdict["description"], iocs=sigdict["iocs"],
            ttps=sigdict["ttps"], tags=sigdict["tags"],
            family=sigdict["family"]
        )

    def update_score(self, score):
        if score <= self.score:
            return

        if score > self.score:
            if score > Scores.KNOWN_BAD:
                self.score = Scores.KNOWN_BAD
            else:
                self.score = score

    def to_dict(self, max_iocs=100, max_ioc_size=20*1024):
        truncated = False
        iocs = list(self.iocs)[0:max_iocs]
        ioc_count = len(self.iocs)
        if len(iocs) < ioc_count:
            truncated = True

        return {
            "name": self.name,
            "short_description": self.short_description,
            "description": self.description,
            "ttps": self.ttps,
            "tags": self.tags,
            "family": self.family,
            "iocs": {
                "truncated": truncated,
                "count": ioc_count,
                "iocs": [ioc.to_dict(max_size=max_ioc_size) for ioc in iocs]
            },
            "score": self.score
        }


class IOC:

    def __init__(self, **kwargs):
        self.ioc = kwargs

    def to_dict(self, max_size=20*1024):
        ioc = {}
        truncated = False
        for k, v in self.ioc.items():
            if isinstance(v, (str, bytes)) and len(v) > max_size:
                msg = " ..value truncated"

                if isinstance(v, bytes):
                    msg = msg.encode()

                truncated = True
                v = v[0:max_size] + msg
            ioc[k] = v

        return {
            "truncated": truncated,
            "ioc": ioc
        }

    def __hash__(self):
        return hash((
            tuple(sorted(hash(k) for k in self.ioc.keys())),
            tuple(sorted(
                hash(v) for v in self.ioc.values()
                if not isinstance(v, (dict, list))
            )),
        ))


class SignatureTracker:

    def __init__(self, tagtracker, ttptracker, familytracker):
        self._triggered_signatures = {}
        self._tag_tracker = tagtracker
        self._ttp_tracker = ttptracker
        self._family_tracker = familytracker

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

    def signatures_to_dict(self, max_iocs=100, max_ioc_size=20*1024):
        return [
            sig.to_dict(max_iocs=max_iocs, max_ioc_size=max_ioc_size)
            for sig in self._triggered_signatures.values()
        ]

    def _add_new_signature(self, score, name, short_description,
                           description="", iocs=[], ttps=[], tags=[],
                           family=""):
        for tag in tags:
            self._tag_tracker.add_tag(tag)

        for ttp in ttps:
            self._ttp_tracker.add_ttp(ttp)

        if family:
            self._family_tracker.add_family(family)

        self._triggered_signatures[name] = Signature(
            score=score, name=name, short_description=short_description,
            description=description, iocs=iocs, ttps=ttps, tags=tags,
            family=family
        )

    def _update_signature(self, signature, score, iocs=[], ttps=[], tags=[],
                          family=""):
        for tag in tags:
            self._tag_tracker.add_tag(tag)
            if tag not in signature.tags:
                signature.tags.append(tag)

        for ttp in ttps:
            self._ttp_tracker.add_ttp(ttp)
            if ttp not in signature.ttps:
                signature.ttps.append(ttp)

        if family:
            self._family_tracker.add_family(family)

        signature.add_iocs(iocs)
        signature.update_score(score)

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
            self._update_signature(
                signature, score=score, iocs=iocs, ttps=ttps, tags=tags,
                family=family
            )
