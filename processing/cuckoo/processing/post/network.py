# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import ipaddress

from cuckoo.common.storage import TaskPaths, Paths
from httpreplay import reader, protohandlers, udpprotoparsers, transport

from ..abtracts import Processor

# TODO move this to a standardized safelist format when there are more things
# to safelist. Leave it here for now until we create a
# 'safelist management tool/way'
class TempSafelist:

    def __init__(self, filepath):
        self._safelist = self._parse(self.read_file(filepath))

    def read_file(self, filepath):
        if not os.path.isfile(filepath):
            return []

        with open(filepath, "r") as fp:
            return set(val.strip() for val in fp.readlines())

    def _parse(self, values):
        pass

    def is_safelisted(self, value):
        pass

class IPSafelist(TempSafelist):

    def _parse(self, values):
        safelist = set()
        for value in values:
            try:
                safelist.add(ipaddress.ip_network(value))
            except (TypeError, ValueError):
                continue

        return safelist

    def is_safelisted(self, value):
        try:
            ip = ipaddress.ip_address(value)
            for network in self._safelist:
                if ip in network:
                    return True
        except (ValueError, TypeError):
            return False

        return False

class Pcapreader(Processor):

    KEY = "network"

    @classmethod
    def init_once(cls):
        cls.ip_safelist = IPSafelist(Paths.safelistfile("ipnetwork.txt"))

    def init(self):
        self.tcp_handlers = {
            25: protohandlers.smtp_handler,
            80: protohandlers.http_handler,
            465: protohandlers.smtp_handler,
            587: protohandlers.smtp_handler,
            8000: protohandlers.http_handler,
            8080: protohandlers.http_handler,
            "generic": protohandlers.forward_handler
        }

        def dns_handler():
            return udpprotoparsers.DNS()

        self.udp_handlers = {
            53: dns_handler,
            "generic": protohandlers.forward_handler
        }

    def start(self):
        pcap_path = TaskPaths.pcap(self.ctx.task.id)
        if not os.path.isfile(pcap_path):
            return

        r = reader.PcapReader(pcap_path)
        r.raise_exceptions = False
        r.set_tcp_handler(transport.TCPPacketStreamer(r, self.tcp_handlers))
        r.set_udp_handler(transport.UDPPacketStreamer(r, self.udp_handlers))

        results = {
            "host": set(),
            "http_request": set(),
            "smtp": set(),
            "dns_query": set(),
            "dns_answer": set()
        }

        for flow, ts, proto, sent, recv in r.process():
            host_index = 2

            # Read sender as dst host if DNS. We use DNS replies for the DNS
            # query and answer at the moment.TODO change this.
            if proto == "dns":
                host_index = 0

            if self.ip_safelist.is_safelisted(flow[host_index]):
                continue

            if proto == "http":
                request = f"{sent.method} " \
                          f"{sent.headers.get('host', flow[2])}" \
                          f":{flow[3]}{sent.uri}"

                results["http_request"].add(request)

            elif proto == "smtp":
                results["smtp"].add(" ".join(sent.raw))

            elif proto == "dns":
                for dns_r in sent:
                    results["dns_query"].add(f"{dns_r.type} {dns_r.name}")

                for dns_a in recv:
                    results["dns_answer"].add(
                        f"{dns_a.type} {dns_a.data} "
                        f"{','.join(dns_a.fields.values())}"
                    )

            host = flow[host_index]
            if flow == self.ctx.machine.ip:
                continue


            results["host"].add(host)

        return {k:list(v) for k, v in results.items()}
