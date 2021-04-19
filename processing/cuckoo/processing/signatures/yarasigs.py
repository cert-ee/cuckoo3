# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import yara

class YaraSignatureError(Exception):
    pass

class MatchedRule:

    def __init__(self, yaramatch):
        self.match = yaramatch

    def trigger_as_signature(self, signature_tracker, scanned_datatype):
        if not self.match.meta.get("short_description"):
            raise YaraSignatureError(
                f"Missing mandatory meta field key 'short_description' "
                f"for Yara signature: {self.match.rule}"
            )

        for k in ("tags", "ttps", "family", "short_description",
                  "description"):
            if not isinstance(self.match.meta.get(k, ""), str):
                raise YaraSignatureError(
                    f"Yara metadata field '{k}' contents must be a string"
                )

        tags = set(
            filter(
                None,
                [t.strip() for t in self.match.meta.get("tags", "").split(",")]
            )
        )
        ttps = set(
            filter(
                None,
                [t.strip() for t in self.match.meta.get("ttps", "").split(",")]
            )
        )
        try:
            score = int(self.match.meta.get("score", 0))
            if score < 0:
                raise ValueError
        except (ValueError, TypeError):
            raise YaraSignatureError(
                "Yara metadata field 'score' must be a positive integer "
                "from 0 to 10"
            )

        signature_tracker.add_signature(
            score=score, name=f"yara_{self.match.rule}",
            short_description=self.match.meta["short_description"],
            description=self.match.meta.get("description"),
            ttps=ttps, tags=tags, family=self.match.meta.get("family"),
            iocs=[{"matched on": scanned_datatype,
                   "yara rule": self.match.rule}]
        )


class YaraFile:

    def __init__(self, path):
        try:
            self._rules = yara.compile(path)
        except yara.Error as e:
            raise YaraSignatureError(
                f"Failed to compile signature: {path}. {e}"
            )

    def match_file(self, filepath):
        return [MatchedRule(m) for m in self._rules.match(filepath)]

    def match_data(self, data):
        return [MatchedRule(m) for m in self._rules.match(data=data)]
