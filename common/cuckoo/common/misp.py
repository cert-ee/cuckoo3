# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import pymisp
import requests.exceptions

from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

class MispError(Exception):
    pass

class ExistingMispEvent:

    def __init__(self, event_dict, searched_ioc, misp_url):
        self._misp_url = misp_url
        self.ioc = searched_ioc
        self.id = event_dict["id"]
        self.description = event_dict["info"]
        self.datetime = datetime.fromtimestamp(int(event_dict["timestamp"]))

    @property
    def event_url(self):
        return urljoin(self._misp_url, f"events/view/{self.id}")

    def to_dict(self):
        return {
            "id": self.id,
            "ioc": self.ioc,
            "description": self.description,
            "datetime": self.datetime.isoformat(),
            "url": self.event_url
        }

class NewMispEvent:

    def __init__(self, info, distribution=None, analysis=None,
                 sharing_group=None, threat_level=None, tags=[]):
        event = pymisp.MISPEvent()
        event.info = info
        if distribution is not None:
            event.distribution = distribution

        if sharing_group is not None:
            event.sharing_group_id = sharing_group

        if analysis is not None:
            event.analysis = analysis

        if threat_level is not None:
            event.threat_level_id = threat_level

        for tag in tags:
            event.add_tag(tag)

        self.event_obj = event

    def set_published(self):
        self.event_obj.publish()

    def add_ip(self, ip, comment=None, intrusion_detection=False):
        self.event_obj.add_attribute(
            "ip-dst", ip, to_ids=intrusion_detection, comment=comment
        )

    def add_domain(self, domain, intrusion_detection=False):
        self.event_obj.add_attribute(
            "domain", domain, to_ids=intrusion_detection
        )

    def add_url(self, url, intrusion_detection=False):
        self.event_obj.add_attribute("url", url, to_ids=intrusion_detection)

    def add_file(self, filename, md5, sha1, sha256, size, media_type,
                 filepath=None, comment=None, intrusion_detection=False):

        fileobj = pymisp.MISPObject("file")
        fileobj.comment = comment
        fileobj.add_attribute("filename", filename).to_ids = False
        fileobj.add_attribute("size-in-bytes", size).to_ids = False
        fileobj.add_attribute("mimetype", media_type).to_ids = False
        fileobj.add_attribute("md5", md5).to_ids = intrusion_detection
        fileobj.add_attribute("sha1", sha1).to_ids = intrusion_detection
        fileobj.add_attribute("sha256", sha256).to_ids = intrusion_detection

        if filepath:
            upload = fileobj.add_attribute("malware-sample", filename)
            upload.data = Path(filepath)

        self.event_obj.add_object(fileobj)

    def add_mutex(self, name, platform, intrustion_detection=False):
        mutexobj = pymisp.MISPObject("mutex")
        mutexobj.add_attribute("name", name).to_ids=intrustion_detection
        mutexobj.add_attribute("operating-system", platform)
        self.event_obj.add_object(mutexobj)

    def add_signature(self, name, description):
        sigobj = pymisp.MISPObject("sb-signature")
        sigobj.add_attribute("software", "Cuckoo 3").to_ids = False
        sigobj.add_attribute("signature", name).to_ids = False
        sigobj.add_attribute("text", description).to_ids = False
        self.event_obj.add_object(sigobj)

    def add_attack_pattern(self, ttpid):
        patternobj = pymisp.MISPObject("attack-pattern")
        patternobj.add_attribute("id", ttpid)
        self.event_obj.add_object(patternobj)

    def add_mitre_attack(self, ttp):
        self.event_obj.add_tag(
            f"misp-galaxy:mitre-attack-pattern=\"{ttp.name} - {ttp.id}\""
        )

    def add_task_info(self, analysis_id, task_id, webinterface_baseurl=None):
        refobj = pymisp.MISPObject("internal-reference")
        # Disable correlation on these attributes so that MISP does not
        # say all Cuckoo events are related to each other. This MISP
        # object type it enabled for all fields by default.
        refobj.add_attribute(
            "comment", f"Task {task_id}"
        ).disable_correlation = True
        refobj.add_attribute(
            "type", "Cuckoo task identifier"
        ).disable_correlation = True
        if webinterface_baseurl:
            # TODO URI is hardcoded. See if we can import this from a constant
            # at some point. Web is a separate package, so cuckoo.common
            # must not depend on it.
            task_url = urljoin(
                webinterface_baseurl, f"analysis/{analysis_id}/task/{task_id}"
            )
            refobj.add_attribute("link", task_url).disable_correlation = True

        self.event_obj.add_object(refobj)


class MispClient:

    def __init__(self, misp_url, api_key, verify_tls=True, timeout=5):
        self._misp_url = misp_url
        try:
            self._client = pymisp.PyMISP(
                url=misp_url, key=api_key, ssl=verify_tls, timeout=timeout
            )
        except (pymisp.PyMISPError, requests.exceptions.RequestException) as e:
            raise MispError(
                f"Failed to create MISP client. Error: {e}"
            ).with_traceback(e.__traceback__)

    def find_event(self, eventid):
        try:
            events = self._client.search(
                eventid=eventid, controller='events'
            )
        except (pymisp.PyMISPError, requests.exceptions.RequestException) as e:
            raise MispError(
                f"Event query failed for value '{eventid}'. "
                f"Type: '{type_attribute}'. Error: {e}"
            ).with_traceback(e.__traceback__)
        try:
            return events[0]
        except (ValueError, TypeError) as e:
            raise MispError(
                f"Failure while reading MISP response JSON. Error: {e}"
            )

    def find_events(self, value, type_attribute=None, limit=1, to_ids=1, publish_timestamp="365d"):
        try:
            attributes = self._client.search(
                value=value, type_attribute=type_attribute, limit=limit,
                metadata=True, return_format="json", object_name=None,
                to_ids=to_ids, publish_timestamp=publish_timestamp,
                controller='attributes'
            )
        except (pymisp.PyMISPError, requests.exceptions.RequestException) as e:
            raise MispError(
                f"Event query failed for value '{value}'. "
                f"Type: '{type_attribute}'. Error: {e}"
            ).with_traceback(e.__traceback__)

        try:
            return [
                ExistingMispEvent(self.find_event(attribute['event_id'])["Event"], value, self._misp_url)
                for attribute in attributes['Attribute']
            ]
        except (ValueError, TypeError) as e:
            raise MispError(
                f"Failure while reading MISP response JSON. Error: {e}"
            )

    def find_file_md5(self, md5, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=md5, type_attribute="md5", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def find_file_sha1(self, sha1, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=sha1, type_attribute="sha1", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def find_file_sha256(self, sha256, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=sha256, type_attribute="sha256", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def find_file_sha512(self, sha512, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=sha512, type_attribute="sha512", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def find_url(self, url, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=url, type_attribute="url", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def find_ip_dst(self, ip, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=ip, type_attribute="ip-dst", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def find_domain(self, domain, limit=1, to_ids=1, publish_timestamp="365d"):
        return self.find_events(
            value=domain, type_attribute="domain", limit=limit,
            to_ids=to_ids, publish_timestamp=publish_timestamp
        )

    def create_event(self, new_misp_event):
        try:
            errors = self._client.add_event(
                new_misp_event.event_obj, pythonify=False
            ).get("errors")

            if errors:
                raise MispError(
                    f"Failed to create new MISP event. "
                    f"Error: {errors[1]}"
                )
        except (pymisp.PyMISPError, requests.exceptions.RequestException) as e:
            raise MispError(f"Failed to create new MISP event. Error: {e}")
