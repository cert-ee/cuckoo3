# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import logging
from datetime import datetime
from urllib.parse import urljoin
import elasticsearch_dsl
import requests

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException

from .log import set_logger_level

set_logger_level("elasticsearch", logging.ERROR)
set_logger_level("urllib3.connectionpool", logging.ERROR)

class IntelMQError(Exception):
    pass

class IntelMQElasticError(IntelMQError):
    pass

class Fields:
    DESTINATION_IP = "destination.ip"
    SOURCE_IP = "source.ip"
    TIME_SOURCE = "time.source"
    TIME_OBSERVATION = "time.observation"
    FEED_NAME = "feed.name"
    FEED_PROVIDER = "feed.provider"
    TAXONOMY = "classification.taxonomy"
    TYPE = "classification.type"
    DESTINATION_FQDN = "destination.fqdn"
    SOURCE_FQDN = "source.fqdn"
    DESTINATION_URL = "destination.url"
    SOURCE_URL = "source.url"
    MALWARE_MD5 = "malware.hash.md5"
    MALWARE_SHA1 = "malware.hash.sha1"
    MALWARE_SHA256 = "malware.hash.sha256"
    MALWARE_NAME = "malware.name"
    FEED_ACCURACY = "feed.accuracy"
    EVENT_DESCRIPTION_TEXT = "event_description.text"
    EVENT_DESCRIPTION_URL = "event_description.url"


class ElasticFields:
    DESTINATION_IP = "destination_ip"
    SOURCE_IP = "source_ip"
    TIME_SOURCE = "time_source"
    TIME_OBSERVATION = "time_observation"
    FEED_NAME = "feed_name"
    FEED_PROVIDER = "feed_provider"
    TAXONOMY = "classification_taxonomy"
    TYPE = "classification_type"
    DESTINATION_FQDN = "destination_fqdn"
    SOURCE_FQDN = "source_fqdn"
    DESTINATION_URL = "destination_url"
    SOURCE_URL = "source_url"
    MALWARE_MD5 = "malware_hash_md5"
    MALWARE_SHA1 = "malware_hash_sha1"
    MALWARE_SHA256 = "malware_hash_sha256"
    FEED_ACCURACY = "feed_accuracy"


class IntelMQEventMaker:

    # https://github.com/certtools/intelmq/blob/develop/intelmq/bots/collectors/api/collector_api.py
    PUSH_ENDPOINT = "/intelmq/push"

    def __init__(self, analysis_id, task_id, webinterface_baseurl=None,
                 feed_accuracy=None, event_description=None):
        self._task_id = task_id
        self._analysis_id = analysis_id
        self._events = []
        self._web_baseurl = webinterface_baseurl
        self._feed_accuracy = feed_accuracy
        self._description = event_description

    def _add_event(self, event_dict, taxonomy, classification_type):
        event_dict.update({
            Fields.TIME_SOURCE: datetime.utcnow().isoformat(),
            Fields.TAXONOMY: taxonomy,
            Fields.TYPE: classification_type
        })
        if self._feed_accuracy is not None:
            event_dict[Fields.FEED_ACCURACY] = self._feed_accuracy

        if self._web_baseurl:
            event_dict[Fields.EVENT_DESCRIPTION_URL] = urljoin(
                self._web_baseurl,
                f"analysis/{self._analysis_id}/task/{self._task_id}"
            )

        if self._description:
            event_dict[Fields.EVENT_DESCRIPTION_TEXT] = self._description

        self._events.append(event_dict)

    def add_dst_ip(self, ip):
        self._add_event(
            {Fields.DESTINATION_IP: ip},
            taxonomy="malicous-code", classification_type="infected-system"
        )

    def add_dst_domain(self, domain):
        self._add_event(
            {Fields.DESTINATION_FQDN: domain},
            taxonomy="malicous-code", classification_type="infected-system"
        )

    def add_dst_url(self, url):
        self._add_event(
            {Fields.DESTINATION_FQDN: domain},
            taxonomy="malicous-code", classification_type="infected-system"
        )

    def add_malware_file(self, md5, sha1, sha256, family=None):
        event = {
            Fields.MALWARE_MD5: md5,
            Fields.MALWARE_SHA1: sha1,
            Fields.MALWARE_SHA256: sha256
        }
        if family:
            event[Fields.MALWARE_NAME] = family

        self._add_event(
            event, taxonomy="malicious-code",
            classification_type="infected-system"
        )

    def submit(self, api_url, verify_tls=True):
        if not self._events:
            return

        endpoint = urljoin(api_url, self.PUSH_ENDPOINT)

        events = "\n".join([json.dumps(event) for event in self._events])
        try:
            requests.post(
                endpoint, data=events, verify=verify_tls
            ).raise_for_status()
        except requests.exceptions.RequestException as e:
            raise IntelMQError(
                f"Failed to POST events to IntelMQ collector API: {e}"
            )


class IntelMQElastic:
    def __init__(self, elastic_hosts, index_name, event_limit=10, link_url=""):
        self._index_name = index_name
        self._limit = event_limit
        self._link_url = link_url
        self._es = Elasticsearch(elastic_hosts, timeout=60)

    def verify(self):
        if not self._es.ping():
            raise IntelMQElasticError(
                f"Could not connect to IntelMQ Elasticsearch host(s)"
            )

        if not self._es.indices.exists(
                self._index_name, allow_no_indices=False
        ):
            raise IntelMQElasticError(
                f"Index with (wildcard)name does not exist: {self._index_name}"
            )

    def _make_event_dicts(self, hits, ioc):
        events = []
        for hit in hits:
            d = hit.to_dict()
            event = {
                ElasticFields.FEED_NAME:d.get(ElasticFields.FEED_NAME, ""),
                ElasticFields.FEED_PROVIDER: d.get(
                    ElasticFields.FEED_PROVIDER, ""
                ),
                ElasticFields.FEED_ACCURACY: d.get(
                    ElasticFields.FEED_ACCURACY, ""
                ),
                ElasticFields.TAXONOMY: d.get(ElasticFields.TAXONOMY, ""),
                ElasticFields.TYPE: d.get(ElasticFields.TYPE, ""),
                ElasticFields.TIME_OBSERVATION: d.get(
                    ElasticFields.TIME_OBSERVATION, ""
                ),
                ElasticFields.TIME_SOURCE: d.get(
                    ElasticFields.TIME_SOURCE, ""
                ),
                "ioc": ioc,
                "index": hit.meta.index,
                "id": hit.meta.id,
                "url": ""
            }

            if self._link_url:
                event["url"] = urljoin(
                    self._link_url, f"{hit.meta.index}/_doc/{hit.meta.id}"
                )

            events.append(event)
        return events

    def _do_query(self, value, fields=[]):

        search = elasticsearch_dsl.Search(
            using=self._es, index=self._index_name
        )
        if len(fields) > 1:
            q = search.query("multi_match", fields=fields, query=value)
        else:
            q = search.query("match", **{fields[0]: value})

        q = q[0:self._limit]
        # Sort the events by the time of occurrence of the event as reported
        # to the feed.
        q = q.sort({ElasticFields.TIME_SOURCE: {"order": "desc"}})
        try:
            response = q.execute()
        except ElasticsearchException as e:
            raise IntelMQElasticError(f"Error while performing query: {e}")

        if not response.hits:
            return []

        return self._make_event_dicts(response.hits, value)

    def find_ip(self, ip):
        return self._do_query(
            ip, fields=[ElasticFields.SOURCE_IP, ElasticFields.DESTINATION_IP]
        )

    def find_domain(self, domain):
        return self._do_query(
            domain, fields=[
                ElasticFields.SOURCE_FQDN, ElasticFields.DESTINATION_FQDN
            ]
        )

    def find_url(self, url):
        return self._do_query(
            url, fields=[
                ElasticFields.DESTINATION_URL, ElasticFields.SOURCE_URL
            ]
        )

    def find_file_md5(self, md5):
        return self._do_query(
            md5, fields=[ElasticFields.MALWARE_MD5]
        )

    def find_file_sha1(self, sha1):
        return self._do_query(
            sha1, fields=[ElasticFields.MALWARE_SHA1]
        )

    def find_file_sha256(self, sha256):
        return self._do_query(
            sha256, fields=[ElasticFields.MALWARE_SHA256]
        )
