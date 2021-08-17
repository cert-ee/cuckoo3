# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import json
import time

from suricatasc import SuricataSC, SuricataException

from cuckoo.common.config import cfg
from cuckoo.common.storage import TaskPaths

from ..abtracts import Processor
from ..errors import DisablePluginError, PluginError
from ..signatures.signature import Levels

class SuricataPcap(Processor):

    ORDER = 999
    KEY = "suricata"

    # Map of classification.config descriptions to signature
    # class types. Used to only use signatures of a specific classtype.
    # unfortunately we need this because the alerts only contain the
    # full description.
    classification_map = {}

    @classmethod
    def enabled(cls):
        return cfg("suricata.yaml", "enabled", subpkg="processing")

    @staticmethod
    def _make_connected_client(sockpath):
        client = SuricataSC(sockpath)
        client.connect()
        return client

    @classmethod
    def _load_classification_mapping(cls, file_path):
        # Parse suricata classification.config and map the descriptions
        # to the class types. This is needed because the triggered alerts only
        # contain the friendly name/description. Not the actual class type.
        # Example entry:
        # config classification: not-suspicious,Not Suspicious Traffic,3\n
        with open(file_path, "r") as fp:
            for line in fp.readlines():
                if not line or line.startswith("#"):
                    continue

                entry = line.split(":", 1)
                if len(entry) != 2 \
                        or entry[0].strip() != "config classification":
                    continue

                # Entry of classtype,description,severity. Ignore if it is not
                # exactly what we expect.
                cls_desc_sev = entry[1].split(",", 2)
                if len(cls_desc_sev) != 3:
                    continue

                description = cls_desc_sev[1].strip()
                classtype = cls_desc_sev[0].strip()

                cls.classification_map[description] = classtype

    @classmethod
    def init_once(cls):
        cls.sock = cfg(
            "suricata.yaml", "unix_sock_path", subpkg="processing"
        )
        cls.evelog_name = cfg(
            "suricata.yaml", "evelog_filename", subpkg="processing"
        )
        cls.classtype_scores = cfg(
            "suricata.yaml", "classtype_scores", subpkg="processing"
        )
        cls.ignore_sigids = cfg(
            "suricata.yaml", "ignore_sigids", subpkg="processing"
        )
        cls.process_timeout = cfg(
            "suricata.yaml", "process_timeout", subpkg="processing"
        )

        try:
            cls._make_connected_client(cls.sock)
        except (SuricataException, OSError) as e:
            raise PluginError(
                f"Failed to connect to Suricata unix socket: Error: {e}"
            )

        path = cfg(
            "suricata.yaml", "classification_config", subpkg="processing"
        )
        cls._load_classification_mapping(path)
        if not cls.classification_map:
            raise PluginError(
                f"No signature classifications read from "
                f"configuration file {path}."
            )

    def init(self):
        try:
            self.client = self._make_connected_client(self.sock)
        except (SuricataException, OSError) as e:
            raise DisablePluginError(
                f"Failed to connect to Suricata unix socket: Error: {e}"
            )

    def _send_command(self, command, argsdict=None):
        try:
            msg = self.client.send_command(command, argsdict)
            if msg.get("return", "").lower() != "ok":
                self.ctx.log.warning(
                    "Unexpected return state from Suricata for command",
                    command=command, args=argsdict, respone=msg
                )
                return None, False

            return msg, True
        except (SuricataException, OSError) as e:
            self.ctx.log.warning(
                "Error sending command to Suricata", comand=command,
                args=argsdict, error=e
            )
            return None, False

    def _send_pcap_command(self, pcap_path, result_dir):
        _, success = self._send_command(
            "pcap-file", {
                "filename": str(pcap_path),
                "output-dir": str(result_dir)
            }
        )
        return success

    def _wait_complete(self, pcap_path):
        waited = 0
        while True:
            msg, success = self._send_command("pcap-file-list")
            if not success:
                return False

            # If our submitted pcap is still in the file list, it is not
            # done and we need to wait.
            if str(pcap_path) not in msg.get("message", {}).get("files", []):

                # Pcap is no longer queued. Check if it is the current pcap
                # being processed. If not, it should be done.
                msg, success = self._send_command("pcap-current")
                if not success:
                    return False

                if msg.get("message") != str(pcap_path):
                    return True

            if waited >= self.process_timeout:
                self.ctx.log.warning(
                    "Pcap waiting timeout reached",
                    timeout=self.process_timeout, waited=waited
                )
                return False

            waited += 1
            time.sleep(1)

    def _make_filtered_event(self, event):
        alert = event.get("alert")
        event = {
            "dstip": event.get("dest_ip", ""),
            "dstport": event.get("dest_port", ""),
            "srcip": event.get("src_ip"),
            "srcport": event.get("src_port"),
            "proto": event.get("proto"),
            "app_proto": event.get("app_proto"),
            "signature_id": alert["signature_id"],
            "signature": alert.get("signature"),
            "category": alert["category"],
            "gid": alert.get("gid"),
            "rev": alert.get("rev")
        }

        malware_families = alert.get("metadata", {}).get(
            "malware_family", []
        )
        if malware_families:
            event["malware_families"] = malware_families

        return event

    def _handle_alert_event(self, event):
        alert = event.get("alert")
        classtype = self.classification_map.get(alert.get("category"))
        sigid = event.get("signature_id")
        if not classtype:
            self.ctx.log.warning(
                "Could not find class type for signature category",
                signature_id=sigid, category=alert.get("category")
            )
            return

        score_level = self.classtype_scores.get(classtype)
        # Ignore alert/signature if the class type of alert/signature is not
        # mapped to any score or the signature id is in the ignore list.
        if score_level is None or sigid in self.ignore_sigids:
            return

        score = Levels.to_score(score_level)
        event = self._make_filtered_event(event)
        iocs = [{
            "signature_id": event["signature_id"],
            "signature": event["signature"],
            "category": event["category"],
            "app_proto": event["app_proto"],
            "src": f"{event['srcip']}:{event['srcport']}",
            "dst": f"{event['dstip']}:{event['dstport']}"
        }]

        self.ctx.signature_tracker.add_signature(
            score=score,
            name="suricata_alert",
            short_description="One or more Suricata signatures matched",
            iocs=iocs
        )

        for family in event.get("malware_families", []):
            self.ctx.signature_tracker.add_signature(
                score=score,
                name="suricata_alert",
                short_description="One or more Suricata signatures matched",
                family=family
            )

        return event

    def _process_eve_log(self, eve_path):
        with open(eve_path, "r") as fp:
            while True:
                event = fp.readline()
                if not event:
                    return

                try:
                    event = json.loads(event)
                except json.JSONDecodeError as e:
                    self.ctx.log.warning("Invalid JSON in eve.log", error=e)
                    # Return as the eve should always be JSON. No use in
                    # continuing reading entries that are all likely invalid.
                    return

                # We are only interested in actual alerts. Ignore everything
                # else.
                if event.get("event_type") != "alert":
                    continue

                filtered_event = self._handle_alert_event(event)
                if filtered_event:
                    yield filtered_event

    def start(self):
        pcap_path = TaskPaths.pcap(self.ctx.task.id)
        if not pcap_path.is_file():
            return

        suricata_dir = TaskPaths.suricata(self.ctx.task.id)
        if not suricata_dir.is_dir():
            suricata_dir.mkdir()

        if not self._send_pcap_command(pcap_path, suricata_dir):
            return

        if not self._wait_complete(pcap_path):
            return

        eve_path = suricata_dir.joinpath(self.evelog_name)
        if not eve_path.is_file():
            self.ctx.log.warning(
                "Eve.json not found after Suricata finished", path=eve_path
            )
            return

        return list(self._process_eve_log(eve_path))
