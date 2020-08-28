# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os.path

from cuckoo.common.config import cfg
from cuckoo.common.elastic import (
    index_analysis, index_events, ElasticSearchError
)
from cuckoo.common.startup import init_elasticsearch
from cuckoo.common.storage import TaskPaths

from ..abtracts import Reporter
from ..translate.events import Kinds

class ElasticSearch(Reporter):

    @classmethod
    def enabled(cls):
        return cfg("reporting", "elasticsearch", "enabled")

    @classmethod
    def init_once(cls):
        init_elasticsearch(create_missing_indices=True)

    def report_pre_analysis(self):
        try:
            index_analysis(self.ctx.analysis, self.ctx.result.get("target"))
        except ElasticSearchError as e:
            self.ctx.log.warning("Failed to index analysis.", error=e)

    def _make_subtype_values(self, eventfile, values_key, checkfunc):
        subtype_values = {}
        with open(eventfile, "r") as fp:
            while True:
                line = fp.readline()
                if not line:
                    break

                try:
                    decoded = json.loads(line)
                except json.JSONDecodeError as e:
                    self.ctx.log.warning(
                        "Failure reading entry from file events file", error=e
                    )

                if checkfunc and not checkfunc(decoded):
                    continue

                value = decoded.get(values_key)
                if not value:
                    continue

                subtype_values.setdefault(decoded["effect"], []).append(value)

        return subtype_values

    def report_post_analysis(self):

        eventype_key_checkfunc = {
            Kinds.FILE: ("srcpath", None),
            Kinds.REGISTRY: ("path", None),
            Kinds.PROCESS: ("command", None)
        }

        for eventtype, key_checkfunc in eventype_key_checkfunc.items():
            eventfile_path = TaskPaths.eventlog(
                self.ctx.task.id, f"{eventtype}.json"
            )
            if not os.path.isfile(eventfile_path):
                continue

            key, checkfunc = key_checkfunc
            subtypes_values = self._make_subtype_values(
                eventfile_path, values_key=key, checkfunc=checkfunc
            )
            if not subtypes_values:
                continue

            for subtype, values in subtypes_values.items():
                try:
                    index_events(
                        analysis_id=self.ctx.analysis.id, eventtype=eventtype,
                        subtype=subtype, values=values,
                        task_id=self.ctx.task.id
                    )
                except ElasticSearchError as e:
                    self.ctx.log.warning(
                        "Failed to index events.", error=e, type=eventtype,
                        subtype=subtype
                    )
