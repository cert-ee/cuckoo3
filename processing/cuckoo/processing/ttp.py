# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

import json


class TTPError(Exception):
    pass


class TTPFileError(TTPError):
    pass


class TTPNotFound(TTPError):
    pass


class MitreAttackTTP:
    def __init__(self, ttp_id, name, tactics, reference_link, subtechniques=[]):
        self.id = ttp_id
        self.name = name
        self.tactics = tactics
        self.reference = reference_link
        self.subtechniques = subtechniques

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "tactics": self.tactics,
            "reference": self.reference,
            "subtechniques": self.subtechniques,
        }


class _MitreAttackTTPLookup:
    def __init__(self, attack_json_path):
        self._mapping = {}
        try:
            self._load(attack_json_path)
        except (KeyError, json.JSONDecodeError) as e:
            raise TTPFileError(
                f"Invalid or missing value in Mitre attack mapping file. "
                f"{attack_json_path}. Error: {e}"
            )

    def _load(self, attack_json_path):
        with open(attack_json_path, "r") as fp:
            ttp_file = json.load(fp)

        for ttp_id, technique in ttp_file.items():
            self._mapping[ttp_id] = MitreAttackTTP(
                ttp_id=ttp_id,
                name=technique["name"],
                tactics=technique["tactics"],
                reference_link=technique["reference"],
                subtechniques=technique.get("subtechniques", []),
            )

    def find(self, ttp_id):
        ttp = self._mapping.get(ttp_id)
        if not ttp:
            log.warning("Unknown/Unmapped Mitre attack TTP", ttp=ttp_id)

        return ttp


class TTPTracker:
    lookup = None

    def __init__(self):
        self._ttps = set()

    @classmethod
    def init_once(cls, attack_json_path):
        cls.lookup = _MitreAttackTTPLookup(attack_json_path)

    @property
    def ttps(self):
        return list(self._ttps)

    def add_ttp(self, ttp_id):
        ttp = self.lookup.find(ttp_id)
        if ttp:
            self._ttps.add(ttp)

    def to_dict(self):
        return [ttp.to_dict() for ttp in self._ttps]
