# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ipaddress
import logging
import os

from cuckoo.common.log import set_logger_level
from cuckoo.common.storage import TaskPaths, Paths
from cuckoo.common import safelist
from httpreplay import reader, protohandlers, udpprotoparsers, transport

from ..abtracts import Processor

set_logger_level("httpreplay.transport", logging.ERROR)
set_logger_level("httpreplay.protoparsers", logging.ERROR)

class Pcapreader(Processor):

    KEY = "network"
    ORDER = 1

    @classmethod
    def init_once(cls):
        cls.ip_sl = safelist.IP()
        cls.domain_sl = safelist.Domain()
        cls.dnsserver_sl = safelist.DNSServerIP()
        cls.ip_sl.load_safelist()
        cls.domain_sl.load_safelist()
        cls.dnsserver_sl.load_safelist()

    def init(self):
        self.ip_sl.clear_temp()

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
            "url": set(),
            "smtp": set(),
            "dns_query": set(),
            "dns_answer": set(),
            "domain": set()
        }

        for flow, ts, proto, sent, recv in r.process():

            host_index = 2

            # Read sender as dst host if DNS. We use DNS replies for the DNS
            # query and answer at the moment.TODO change this.
            if proto == "dns":
                host_index = 0

            if self.ip_sl.is_safelisted(flow[host_index]):
                continue

            if proto == "http":
                host = sent.headers.get('host', flow[2])
                port = ""
                if flow[3] != 80:
                    port = f":{flow[3]}"

                url = f"http://{host}{port}{sent.uri}"
                request = f"{sent.method} {url}"
                results["http_request"].add(request)
                results["url"].add(url)

            elif proto == "smtp":
                results["smtp"].add(" ".join(sent.raw))

            elif proto == "dns":

                safelist_reply = False
                source_domain = ""
                for dns_r in sent:
                    if dns_r.type in ("A", "AAAA"):
                        if self.domain_sl.is_safelisted(
                                    dns_r.name, self.ctx.machine.platform
                        ):
                            safelist_reply = True
                            source_domain = dns_r.name
                            continue

                    results["dns_query"].add(f"{dns_r.type} {dns_r.name}")
                    results["domain"].add(dns_r.name)


                for dns_a in recv:
                    if safelist_reply:
                        if dns_a.type in ("A", "AAAA"):
                            self.ip_sl.add_temp_entry(
                                dns_a.data,
                                platform=self.ctx.machine.platform,
                                description="Auto safelist based on domain",
                                source=f"Safelisted domain: {source_domain}"
                            )
                        continue

                    results["dns_answer"].add(
                        f"{dns_a.type} {dns_a.data} "
                        f"{','.join(dns_a.fields.values())}"
                    )


            host = flow[host_index]
            if host == self.ctx.machine.ip:
                continue

            # If the DNS server is safelisted, do not add it to the hosts list.
            if proto == "dns" and self.dnsserver_sl.is_safelisted(host):
                continue

            results["host"].add(host)

        return {
            "summary": {k:list(v) for k, v in results.items()}
        }
