# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import logging
import time
import re
from collections import OrderedDict
from pathlib import Path

import elasticsearch_dsl
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException, TransportError

from .log import set_logger_level, CuckooGlobalLogger

set_logger_level("elasticsearch", logging.ERROR)
set_logger_level("urllib3.connectionpool", logging.ERROR)

log = CuckooGlobalLogger(__name__)

class ElasticSearchError(Exception):
    pass

class SearchError(ElasticSearchError):
    pass

class _Indices:
    EVENTS = "events"
    ANALYSES = "analyses"
    TASKS = "tasks"

class _ESManager:

    index_mapping_filename = {
        _Indices.ANALYSES: "analysesmapping.json",
        _Indices.TASKS: "tasksmapping.json",
        _Indices.EVENTS: "eventsmapping.json"
    }

    def __init__(self):
        self._initialized = False
        self._names_realnames = {
            _Indices.EVENTS: None,
            _Indices.ANALYSES: None,
            _Indices.TASKS: None
        }

        self._client = None
        self._hosts = []
        self._max_result_window = 0

    @property
    def client(self):
        if not self._initialized:
            raise ElasticSearchError(
                "Elasticsearch manager not configured. Cannot perform any "
                "Elasticsearch actions with client."
            )
        return self._client

    @property
    def max_result_window(self):
        if not self._initialized:
            raise ElasticSearchError(
                "Elasticsearch manager not initialized. Cannot retrieve max "
                "results window"
            )

        return self._max_result_window

    def index_realname(self, name):
        if not self._initialized:
            raise ElasticSearchError(
                "Elasticsearch manager not initialized. Cannot lookup real "
                "index name."
            )
        return self._names_realnames[name]

    def configure(self, hosts, analyses_index, tasks_index, events_index,
                  max_result_window=10000, timeout=60):

        self._names_realnames["analyses"] = analyses_index
        self._names_realnames["tasks"] = tasks_index
        self._names_realnames["events"] = events_index

        self._max_result_window = max_result_window
        self._hosts = hosts
        self._client = Elasticsearch(hosts, timeout=timeout)
        self._initialized = True

    def verify(self):
        if not self.client.ping():
            raise ElasticSearchError(
                "Could not connect to Elasticsearch host(s)"
            )

    def all_indices_exist(self):
        self.verify()
        return len(self._get_existing_indices()) == len(self._names_realnames)

    def create_missing_indices(self, templates_directory):
        existing = self._get_existing_indices()
        for name, realname in self._names_realnames.items():
            if name in existing:
                continue

            mapping_path = Path(
                templates_directory, self.index_mapping_filename[name]
            )
            if not mapping_path.is_file():
                raise ElasticSearchError(
                    f"Mapping file {mapping_path} for index {name} does not"
                    f" exist."
                )

            with open(mapping_path, "r") as fp:
                try:
                    index_mapping = json.load(fp)
                except json.JSONDecodeError as e:
                    raise ElasticSearchError(
                        f"Invalid JSON in index mapping file {mapping_path}. "
                        f"Error: {e}"
                    )

            self._create_index(realname, index_mapping)

    def _get_existing_indices(self):
        existing = []
        for name, realname in self._names_realnames.items():
            try:
                if self.client.indices.exists(realname):
                    existing.append(name)
            except ElasticsearchException as e:
                raise ElasticSearchError(
                    f"Failure while determining existing indices. {e}"
                )

        return existing

    def _create_index(self, name, index_mapping):
        try:
            self.client.indices.create(name, body=index_mapping)
            log.debug("Created index", index_name=name)
        except ElasticsearchException as e:
            if isinstance(e, TransportError):
                # If the index already exists, ignore the error. This case
                # can happen if we have multiple processes that try to create
                # an index.
                if e.error == "resource_already_exists_exception":
                    return

            raise ElasticSearchError(
                f"Failed to create index {name}. Error: {e}"
            ).with_traceback(e.__traceback__)


manager = _ESManager()

_PREFIX_INDEX = {
    "event": _Indices.EVENTS,
    "analysis": _Indices.ANALYSES,
    # "task": _Indices.TASKS
}

_INDEX_KEYWORDS = {
    _Indices.EVENTS: ("task_id", "analysis_id", "type", "subtype"),
    _Indices.ANALYSES: (
        "analysis_id", "category", "submitted.md5", "submitted.sha1",
        "submitted.sha256", "target.md5", "target.sha1",
        "target.sha256"
    )
}

_FILTER_PREFIXES = tuple(_PREFIX_INDEX.keys())

def _make_ts():
    return int(str(time.time()).replace(".", ""))

def index_events(analysis_id, eventtype, values, subtype=None, task_id=None):

    doc_id = f"{task_id}{eventtype}{subtype if subtype else ''}"

    body = {
        "ts": _make_ts(),
        "analysis_id": analysis_id,
        "type": eventtype,
        "values": values
    }
    if task_id:
        body["task_id"] = task_id
    if subtype:
        body["subtype"] = subtype

    try:
        manager.client.index(index="events", id=doc_id, body=body)
    except ElasticsearchException as e:
        raise ElasticSearchError(
            f"Failed to create event entry in Elasticsearch. {e}"
        )

def index_analysis(analysis, target):
    body = {
        "ts": _make_ts(),
        "analysis_id": analysis.id,
        "category": analysis.category,
        "settings": {
            "timeout": analysis.settings.timeout
        }
    }

    submitted = analysis.submitted
    if analysis.category == "url":
        body["submitted"] = {
            "url": submitted.url
        }
        body["target"] = {
            "url": target.url
        }
    elif analysis.category == "file":
        body["submitted"] = {
            "filename": submitted.filename,
            "size": submitted.size,
            "md5": submitted.md5,
            "sha1": submitted.sha1,
            "sha256": submitted.sha256,
            "media_type": submitted.media_type,
            "magic": submitted.type
        }
        body["target"] = {
            "filename": target.filename,
            "size": target.size,
            "md5": target.md5,
            "sha1": target.sha1,
            "sha256": target.sha256,
            "media_type": target.media_type,
            "magic": target.filetype
        }
        try:
            manager.client.index(index="analyses", id=analysis.id, body=body)
        except ElasticsearchException as e:
            raise ElasticSearchError(
                f"Failed to create analysis entry in Elasticsearch. {e}"
            )

_query_pattern = {
    "analysis.target.md5": re.compile("^[a-f0-9]{32}$", re.IGNORECASE),
    "analysis.target.sha1": re.compile("^[a-f0-9]{40}$", re.IGNORECASE),
    "analysis.target.sha256": re.compile("^[a-f0-9]{64}$", re.IGNORECASE)
}

class _SearchQueryParser:

    def __init__(self, query):
        self._raw = query

        self._searches = {}
        self._search_preparators = {
            "events": self._add_event_search,
            "analyses": self._add_analysis_search
        }

        self.parse()

    def _add_event_search(self, filter_fields, argsstr):
        search = {}
        if len(filter_fields) == 1:
            search = {"type": filter_fields[0], "values": argsstr}

        elif len(filter_fields) == 2:
            search = {
                "type": filter_fields[0],
                "subtype":filter_fields[1],
                "values": argsstr
            }

        if search:
            if self._has_wildcard(argsstr):
                self._add_wildcard_indicator(search)

            self._searches.setdefault(_Indices.EVENTS, []).append(search)
            return


        raise SearchError(
            f"No further subkey possible after {filter_fields[1]!r}"
        )

    def _add_analysis_search(self, filter_fields, argsstr):

        fields_path = ".".join(filter_fields)
        search = {"path": fields_path, "value": argsstr}

        searches = self._searches.setdefault(_Indices.ANALYSES, [])

        # If this fieldpath is a keyword, insert it at the front to ensure
        # it will be the first query performed for this index.
        if fields_path.endswith(_INDEX_KEYWORDS[_Indices.ANALYSES]):
            searches.insert(0, search)
            return

        if self._has_wildcard(argsstr):
            self._add_wildcard_indicator(search)

        searches.append(search)

    @classmethod
    def _has_wildcard(cls, searchstr):
        return "*" in searchstr

    @classmethod
    def _add_wildcard_indicator(cls, search):
        search["_has_wildcard"] = True

    @classmethod
    def _is_filter(cls, token):
        dotsplit = tuple(filter(None, token.split(".")))

        if dotsplit and dotsplit[0].lower() not in _FILTER_PREFIXES:
            return False

        return ":" in token

    @classmethod
    def _split_filter(cls, filterstr):
        parts = list(filter(None, filterstr.split(":", 1)))
        filters = list(filter(None, parts[0].split(".")))
        if len(parts) > 1:
            return filters, parts[1].strip()

        return filters, ""

    def has_searches(self):
        return len(self._searches) > 0

    def _add_search(self, filter_str):
        filters, args_str = self._split_filter(filter_str)
        if len(filters) < 2:
            raise SearchError(
                f"Filter prefix not followed by actual filter fields. "
                f"{filter_str!r}"
            )

        prefix = filters[0]
        filters = filters[1:]
        index = _PREFIX_INDEX.get(prefix)

        preparator = self._search_preparators.get(index)
        if not preparator:
            raise SearchError(f"Unsupported filter {prefix!r}")

        preparator(filters, args_str)

    def _guess_query(self, token):
        for query, regex in _query_pattern.items():
            if regex.match(token):
                return f"{query}:{token}"

        return None

    def parse(self):
        tokens = self._raw.split(" ")

        nonfilter_tokens = []
        for token in reversed(tokens):
            if self._is_filter(token):
                self._add_search(f"{token} {' '.join(nonfilter_tokens)}")
                nonfilter_tokens = []
            else:
                nonfilter_tokens.insert(0, token)

        if nonfilter_tokens:
            # There are still tokens left that are not an argument to
            # anything. Guess what it is and add it to the query.
            for token in nonfilter_tokens:
                query = self._guess_query(token)
                if query:
                    self._add_search(query)

    def get_searches(self):
        # First return any searches in the analyses index as these can
        # greatly reduce the search space.
        if _Indices.ANALYSES in self._searches:
            searches = self._searches[_Indices.ANALYSES]
            self._searches.pop(_Indices.ANALYSES)

            return _Indices.ANALYSES, searches

        for index in self._searches.keys():
            search = self._searches[index].pop(0)
            if not self._searches[index]:
                self._searches.pop(index)
            return index, [search]

        return None, None

class _SearchResultTracker:

    def __init__(self):
        self._analyses = OrderedDict()
        self._tasks = OrderedDict()
        self._offset = 0

        self.possible_hits = 0

    def _add_result(self, analysis_id, task_id=None, matches=[]):
        if task_id:
            self._add_task_result(analysis_id, task_id, matches)
        else:
            self._add_analysis_result(analysis_id, matches)

    def _add_analysis_result(self, analysis_id, matches):
        self._analyses.setdefault(analysis_id, []).extend(matches)

    def _add_task_result(self, analysis_id, task_id, matches):
        task = self._tasks.setdefault(
            task_id, {"analysis_id": analysis_id, "matches": []}
        )
        task["matches"].extend(matches)

    def _make_match(self, key, valuelist):
        return {"field": key, "matches": valuelist}

    def _make_event_match(self, highlight):
        eventtype = None if "type" not in highlight else highlight.type[0]
        subtype = None if "subtype" not in highlight else highlight.subtype[0]
        values = None if "values" not in highlight else highlight.values
        if not eventtype or not values:
            return []

        if subtype:
            fieldname = f"{eventtype}.{subtype}"
        else:
            fieldname = eventtype

        return [self._make_match(fieldname, list(values))]

    def _make_analysis_match(self, highlight):
        matches = []
        for key in highlight:
            if key in ("analysis_id", "task_id"):
                continue

            matches.append(self._make_match(key, list(highlight[key])))

        return matches

    def set_offset(self, offset):
        self._offset = offset

    def store_result(self, hit):
        analysis_id = hit.analysis_id
        task_id = getattr(hit, "task_id", None)
        index = hit.meta.index

        matches = []
        if task_id and index == _Indices.EVENTS:
            matches = self._make_event_match(hit.meta.highlight)
        elif index == _Indices.ANALYSES:
            matches = self._make_analysis_match(hit.meta.highlight)

        self._add_result(analysis_id, task_id=task_id, matches=matches)

    def store_results(self, hits):
        for hit in hits:
            self.store_result(hit)

    def get_results(self):
        results = []

        if self._tasks:
            for task_id, values in self._tasks.items():
                analysis_id = values["analysis_id"]
                analysis_resuls = self._analyses.get(analysis_id)
                if analysis_resuls:
                    values["matches"].extend(analysis_resuls)

                results.append({
                    "analysis_id": analysis_id,
                    "task_id": task_id,
                    "matches": values["matches"]
                })

        elif self._analyses:
            for analysis_id, matches in self._analyses.items():
                results.append({
                    "analysis_id": analysis_id,
                    "task_id": None,
                    "matches": matches
                })

        return {
            "possible": self.possible_hits,
            "offset": self._offset,
            "count": len(results),
            "matches": results
        }


class _SearchQueryRunner:

    def __init__(self, searchquery, limit=5, offset=0):
        self._query = searchquery
        self.limit = limit

        if limit < 1:
            raise SearchError("Limit cannot be less than 1")

        if offset < 0:
            raise SearchError("Offset cannot be negative")

        self.original_offset = offset

        self._initial = None
        # list of query:query matching_ids:ids dicts
        self._secondaries = []

        self._resulttracker = _SearchResultTracker()

        self._init_query_offset = offset

        if self.limit <= 10:
            self._init_query_limit = 10
        else:
            self._init_query_limit = limit

    def _execute_initial(self):
        return self._execute_query(
            self._add_highlight_query(self._initial),
            limit=self._init_query_limit, offset=self._init_query_offset
        )

    def _execute_secondaries(self, analysis_id):
        all_hits = []
        for query in self._secondaries:
            analysis_query = self._make_termsearch(
                query["query"], "analysis_id", analysis_id
            )
            analysis_query = self._add_highlight_query(analysis_query)
            hits, count = self._execute_query(
                analysis_query, limit=self.limit, offset=0
            )
            if not count:
                return []

            all_hits.append(hits)

        return all_hits

    def _populate_secondary_matches(self):
        for secondary in self._secondaries:
            ids = self._secondary_find_ids(secondary["query"])
            if not ids:
                return False

            secondary["ids"] = ids

        return True

    def _secondary_find_ids(self, query):
        query = query.source(includes=["analysis_id"])
        hits, hitcount = self._execute_query(
            query, limit=manager.max_result_window
        )

        if not hitcount:
            return set()

        return set([hit.analysis_id for hit in hits])

    def _id_matches_secondaries(self, analysis_id):
        for secondary in self._secondaries:
            if analysis_id not in secondary["ids"]:
                return False

        return True

    def _add_highlight_query(self, query):
        return query.highlight(
            "*", fragment_size=255, pre_tags="", post_tags=""
        )

    def _execute_query(self, query, limit=5, offset=0):
        query = query[offset:offset + limit]
        query = query.sort("ts")
        log.debug("Generated query.", query=query.to_dict())
        try:
            response = query.execute()
        except ElasticsearchException as e:
            raise ElasticSearchError(f"Error during query execution: {e}")

        return response.hits, response.hits.total.value

    def _build_queries(self):
        while True:
            index, searches = self._query.get_searches()
            if not index:
                break

            if index == _Indices.EVENTS:
                query = self._make_events_query(searches[0])
            elif index == _Indices.ANALYSES:
                query = self._make_analyses_query(searches)
            else:
                raise SearchError(f"Unknown index: {index}")

            if not self._initial:
                self._initial = query
            else:
                self._add_secondary(query)

    def _add_secondary(self, query):
        self._secondaries.append({
            "query": query,
            "ids": set()
        })

    def _make_termsearch(self, query, path, value):
        return query.query("term", **{path: value})

    def _make_matchsearch(self, query, path, value):
        return query.query("match", **{path: value})

    def _make_querystring(self, query, path, value):
        return query.query("query_string", fields=[path], query=value)

    def _make_analyses_query(self, searches):
        query = elasticsearch_dsl.Search(
            using=manager.client,
            index=manager.index_realname(_Indices.ANALYSES)
        )
        for search in searches:
            path = search["path"]
            value = search["value"]
            if path.endswith(_INDEX_KEYWORDS[_Indices.ANALYSES]):
                query = self._make_termsearch(query, path, value)
            elif "_has_wildcard" in search:
                query = self._make_querystring(query, path, value)
            else:
                query = self._make_matchsearch(query, path, value)

        return query

    def _make_events_query(self, search, analysis_id=None):
        query = elasticsearch_dsl.Search(
            using=manager.client, index=manager.index_realname(_Indices.EVENTS)
        )

        query = self._make_termsearch(query, "type", search["type"])
        if "subtype" in search:
            query = self._make_termsearch(query, "subtype", search["subtype"])

        if "_has_wildcard" in search:
            query = self._make_querystring(query, "values", search["values"])
        else:
            query = self._make_matchsearch(query, "values", search["values"])

        if analysis_id:
            query = self._make_termsearch(query, "analysis_id", analysis_id)

        return query

    def execute(self):
        if not self._query.has_searches():
            return self._resulttracker.get_results()

        self._build_queries()

        # Execute the initial query and use the IDs from that to perform
        # all the secondary queries. If an analysis ID does not match
        # a secondary query, retrieve more IDs using the initial query as long
        # as the amount of fully matched analysis ids has not reached
        # self.limit.
        initialized_secondaries = False
        response_offset = 0
        initial_requested = 0
        full_matches = 0
        while True:
            # Run the initial query. The analysis IDs of matches will be used
            # to perform specific subqueries (the secondaries).
            hits, initial_hitcount = self._execute_initial()
            self._resulttracker.possible_hits = initial_hitcount
            if not hits:
                break

            # No matches are found for the initial search. Stop.
            if not initial_hitcount or self.original_offset >=\
                    initial_hitcount:
                break

            # If no secondary queries have been given. Return the matches
            # for the initial query.
            if not self._secondaries:
                limited = hits[0:self.limit]
                response_offset = len(limited)
                self._resulttracker.store_results(limited)
                break

            if not initialized_secondaries:
                # Create query:analysis_id mappings for all IDs in the index
                # that match the each secondary query. Stop if one of the
                # queries returns 0 results.
                if not self._populate_secondary_matches():
                    break

                initialized_secondaries = True

            # Map the results of each match to the analysis ID, so that they
            # can easily be found if the ID matches the other queries.
            initial_id_result = {hit.analysis_id: hit for hit in hits}
            for analysis_id in [hit.analysis_id for hit in hits]:
                # Increment the offset counter. This is the offset that must
                # be used for the same query with a different offset. We
                # increment it because we keep looking for matches until we
                # have a least self.limit matches.
                response_offset += 1

                # If the analysis id does not match any of the IDs retrieved
                # earlier, ignore it.
                if not self._id_matches_secondaries(analysis_id):
                    continue

                full_matches += 1

                # Perform the actual secondary queries for the given
                # analysis_id because we are now sure a match exists.
                all_hits = self._execute_secondaries(analysis_id)
                for hits in all_hits:
                    self._resulttracker.store_results(hits)

                # Store the matched information of the initial query
                self._resulttracker.store_results(
                    [initial_id_result[analysis_id]]
                )

                if full_matches >= self.limit:
                    break

            # If we have requested more documents or an equal amount as the
            # total available documents. Stop the search before incrementing
            # the offset and performing another initial search for which
            # we know there will be no results.
            initial_requested += len(hits)
            if initial_requested >= initial_hitcount:
                break

            if full_matches >= self.limit:
                break

            self._init_query_offset += self._init_query_limit

        self._resulttracker.set_offset(response_offset + self.original_offset)
        return self._resulttracker.get_results()


def search(querystring, limit=5, offset=0):
    if not isinstance(limit, int) or not isinstance(offset, int):
        raise SearchError("Limit and offset must be an integer")

    if not isinstance(querystring, str):
        raise SearchError("Query must be a string")

    if limit > manager.max_result_window or offset > manager.max_result_window:
        raise SearchError(
            f"Limit or offset is larger than the maximum Elasticsearch "
            f"results window. Max is: {manager.max_result_window}"
        )

    query = _SearchQueryParser(querystring)
    runner = _SearchQueryRunner(query, limit=limit, offset=offset)
    return runner.execute()
