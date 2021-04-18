# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os.path

from cuckoo.common.config import cfg
from cuckoo.common.elastic import (
    index_analysis, index_events, index_task, ElasticSearchError
)
from cuckoo.common.startup import init_elasticsearch
from cuckoo.common.storage import TaskPaths

from ..abtracts import Reporter
from cuckoo.processing.event.events import Kinds

class ElasticSearch(Reporter):

    @classmethod
    def enabled(cls):
        return cfg("reporting", "elasticsearch", "enabled")

    @classmethod
    def init_once(cls):
        init_elasticsearch(create_missing_indices=True)

    def report_pre_analysis(self):
        try:
            index_analysis(
                self.ctx.analysis, self.ctx.result.get("target"),
                self.ctx.signature_tracker.signatures
            )
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

    def _store_behavioral_events(self):
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

    def _make_hosts(self, network):
        return [(network.get("host", []), "host")]

    def _make_domain(self, network):
        return [(network.get("domain", []), "domain")]

    def _make_dns(self, network):
        queries = set()
        responses = set()

        for r in network.get("dns", {}).get("response", []):
            responses.add(
                f"{r['type']} {r['data']} "
                f"{','.join(r.get('fields', {}).values())}"
            )

        for q in network.get("dns", {}).get("query", []):
            queries.add(f"{q['type']} {q['name']}")

        return [
            (list(queries), "dns_query"), (list(responses), "dns_response")
        ]

    def _make_http_request(self, network):
        requests = set()
        urls = set()

        for http in network.get("http", []):
            request = http.get("request")
            if not request:
                continue

            urls.add(request.get('url', ''))
            requests.add(
                f"{request.get('method', '')} {request.get('url', '')}"
            )

        return [(list(requests), "http_request"), (list(urls), "url")]

    def _make_smtp(self, network):
        smtp = []
        for smtp in network.get("smtp", []):
            request = smtp.get("request")
            if not request:
                continue

            smtp.append(
                f"{request.get('hostname', '')} {request.get('mail_body', '')}"
            )

        return [(smtp, "smtp")]

    def _store_network_events(self):
        network = self.ctx.result.get("network", {})
        if not network:
            return

        formatters = [
            self._make_hosts, self._make_domain, self._make_dns,
            self._make_http_request, self._make_smtp
        ]

        for formatter in formatters:
            data_subtypes = formatter(network)
            for data, subtype in data_subtypes:
                if not data:
                    continue

                try:
                    index_events(
                        analysis_id=self.ctx.analysis.id, eventtype="network",
                        subtype=subtype, values=data,
                        task_id=self.ctx.task.id
                    )
                except ElasticSearchError as e:
                    self.ctx.log.warning(
                        "Failed to index events.", error=e, type="network",
                        subtype=subtype
                    )

    def report_post_analysis(self):
        self._store_behavioral_events()
        self._store_network_events()
        try:
            index_task(
                task=self.ctx.task, score=self.ctx.signature_tracker.score,
                machine=self.ctx.machine,
                signatures=self.ctx.signature_tracker.signatures,
                tags=self.ctx.tag_tracker.tags,
                families=self.ctx.family_tracker.families,
                ttps=[t.id for t in self.ctx.ttp_tracker.ttps]
            )
        except ElasticSearchError as e:
            self.ctx.log.warning("Failed to index analysis.", error=e)
