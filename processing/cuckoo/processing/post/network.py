# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import os

from dpkt import http

from cuckoo.common.log import set_logger_level
from cuckoo.common.storage import TaskPaths
from cuckoo.common import safelist
from httpreplay import (
    reader, protohandlers, udpprotoparsers, transport, protoparsers,
    guess
)

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
            "generic": guess.tcp_guessprotocol
        }

        self.udp_handlers = {
            53: protohandlers.DNS,
            "generic": protohandlers.forward_handler
        }

    def _make_http_headers(self, httpdata):
        headers = []
        if not httpdata.headers:
            return headers

        for name, content in httpdata.headers.items():
            # Limit on 20 headers
            if len(headers) >= 20:
                break

            if not isinstance(content, list):
                content = [content]

            for value in content:
                # Limit header and content to 1MB
                mb1 = 1 * 1024 * 1024
                if len(name) > mb1 or len(content) > mb1:
                    continue

                headers.append({
                    "key": name,
                    "value": value
                })

        return headers

    def _make_http_request(self, dst, protocol, request):
        dstip, dstport = dst
        hoststr  = request.headers.get("host", dstip)
        portstr = ""
        if dstport not in (80, 443):
            portstr = f":{dstport}"

        url = f"{protocol}://{hoststr}{portstr}{request.uri}"

        return {
            "version": request.version,
            "url": url,
            "protocol": protocol,
            "method": request.method,
            "headers": self._make_http_headers(request),
            "length": len(request.body)
        }

    def _make_http_response(self, protocol, response):
        return {
            "version": response.version,
            "protocol": protocol,
            "status": int(response.status),
            "headers": self._make_http_headers(response),
            "length": len(response.body)
        }

    def _add_http_entry(self, ts, src, dst, protocol, sent, recv, tracker):
        data = {}
        for httpdata in (sent, recv):
            if not httpdata:
                continue

            if isinstance(httpdata, http.Request):
                data["request"] = self._make_http_request(
                     dst, protocol, httpdata
                )
            elif isinstance(httpdata, http.Response):
                data["response"] = self._make_http_response(
                    protocol, httpdata
                )

        if not data:
            return

        srcip, srcport = src
        dstip, dstport = dst
        data.update({
            "ts": ts,
            "srcip": srcip,
            "srcport": srcport,
            "dstip": dstip,
            "dstport": dstport
        })
        tracker.setdefault("http", []).append(data)

    def _add_smtp(self, ts, src, dst, sent, recv, tracker):
        data = {}
        for smtpdata in (sent, recv):
            if isinstance(smtpdata, protoparsers.SmtpRequest):
                data["request"] = {
                    "hostname": smtpdata.hostname,
                    "mail_from": smtpdata.mail_from,
                    "mail_to": smtpdata.mail_to,
                    "auth_type": smtpdata.auth_type,
                    "username": smtpdata.username,
                    "password": smtpdata.password,
                    "headers": smtpdata.headers,
                    "mail_body": smtpdata.message
                }
            elif isinstance(smtpdata, protoparsers.SmtpReply):
                data["response"] = {
                    "banner": smtpdata.ready_message
                }

        if not data:
            return

        srcip, srcport = src
        dstip, dstport = dst
        data.update({
            "ts": ts,
            "srcip": srcip,
            "srcport": srcport,
            "dstip": dstip,
            "dstport": dstport
        })
        tracker.setdefault("smtp", []).append(data)

    def _add_tcp(self, ts, src, dst, proto, sent, recv, tracker):
        srcip, srcport = src
        dstip, dstport = dst
        tcp = {
            "ts": ts,
            "dstip": dstip,
            "dstport": dstport,
            "srcip": srcip,
            "srcport": srcport
        }
        if sent:
            tcp["tx_size"] = len(sent)
        if recv:
            tcp["rx_size"] = len(recv)

        tracker.setdefault("tcp", []).append(tcp)

        if proto in ("http", "https"):
            self._add_http_entry(ts, src, dst, proto, sent, recv, tracker)
        elif proto == "smtp":
            self._add_smtp(ts, src, dst, sent, recv, tracker)

    def _add_dns(self, ts, src, dst, proto, data, tracker):
        srcip, srcport = src
        dstip, dstport = dst

        dns = tracker.setdefault("dns", {})
        if isinstance(data, udpprotoparsers.DNSQueries):
            # Only use domain safelist if used DNS server is safelisted.
            usesafelist = self.dnsserver_sl.is_safelisted(
                dstip, platform=self.ctx.machine.platform
            )

            queries = dns.setdefault("query", [])
            for q in data.queries:
                if usesafelist and self.domain_sl.is_safelisted(
                        q.name, self.ctx.machine.platform
                ):
                    continue

                queries.append({
                    "ts": ts,
                    "dstip": dstip,
                    "dstport": dstport,
                    "srcip": srcip,
                    "srcport": srcport,
                    "type": q.type,
                    "name": q.name,
                })

        elif isinstance(data, udpprotoparsers.DNSResponses):
            # Only use domain safelist if used DNS server is safelisted.
            usesafelist = self.dnsserver_sl.is_safelisted(
                srcip, platform=self.ctx.machine.platform
            )

            answers = dns.setdefault("response", [])
            domains = tracker.setdefault("domain", [])
            safelisted_domains = []
            for q in data.queries:
                if not q.type in ("A", "AAAA"):
                    continue

                if usesafelist and self.domain_sl.is_safelisted(q.name):
                    safelisted_domains.append(q.name)
                elif not q.name in domains:
                    domains.append(q.name)

            for r in data.responses:
                if usesafelist and safelisted_domains:
                    # Temporarily safelist IP from resolved safelisted domain.
                    if r.type in ("A", "AAAA"):
                        try:
                            self.ip_sl.add_temp_entry(
                                r.data,
                                platform=self.ctx.machine.platform,
                                description="Auto safelist based on "
                                            "safelisted domain",
                                source=f"Safelisted domain(s):"
                                       f" {', '.join(safelisted_domains)}"
                            )
                        except safelist.SafelistError as e:
                            self.ctx.log.warning(
                                "Failed to add IP to temporary safelist for "
                                "safelisted domain", error=e,
                                domain=safelisted_domains[0]
                            )

                    continue

                ans = {
                    "ts": ts,
                    "dstip": dstip,
                    "dstport": dstport,
                    "srcip": srcip,
                    "srcport": srcport,
                    "type": r.type,
                    "data": r.data
                }
                if r.fields:
                    ans["fields"] = r.fields

                answers.append(ans)

    def _add_udp(self, ts, src, dst, proto, data, tracker):
        srcip, srcport = src
        dstip, dstport = dst

        tracker.setdefault("udp", []).append({
            "ts": ts,
            "dstip": dstip,
            "dstport": dstport,
            "srcip": srcip,
            "srcport": srcport,
            "size": len(data)
        })
        if proto == "dns":
            self._add_dns(ts, src, dst, proto, data, tracker)

    def start(self):
        pcap_path = TaskPaths.pcap(self.ctx.task.id)
        if not os.path.isfile(pcap_path):
            return

        r = reader.PcapReader(pcap_path)
        r.raise_exceptions = False
        r.set_tcp_handler(transport.TCPPacketStreamer(r, self.tcp_handlers))
        r.set_udp_handler(transport.UDPPacketStreamer(r, self.udp_handlers))

        results = {}
        hosts = results.setdefault("host", [])
        for flow, ts, proto, sent, recv in r.process():
            src_host = flow[0]
            dst_host = flow[2]
            # Non-dns destination IP is safelisted for the current platform.
            # Ignore completely.
            if proto != "dns":
                is_safelisted = False
                for host in (src_host, dst_host):
                    if host == self.ctx.machine.ip:
                        continue

                    if self.ip_sl.is_safelisted(
                            host, self.ctx.machine.platform
                    ):
                        is_safelisted = True

                # Src or dst IP is part of a safelisted network. Skip this
                # traffic.
                if is_safelisted:
                    continue

            if proto in ("tls", "tcp", "http", "https", "smtp"):
                self._add_tcp(
                    ts, (flow[0], flow[1]), (flow[2], flow[3]), proto,
                    sent, recv, results
                )
            elif proto in ("udp", "dns"):
                self._add_udp(
                    ts, (flow[0], flow[1]), (flow[2], flow[3]), proto, sent,
                    results
                )

            for host in (src_host, dst_host):

                # Do not log the machine IP as a contacted host
                if host == self.ctx.machine.ip:
                    continue

                # Do not log a safelisted DNS server as a contacted host.
                if proto == "dns" and self.dnsserver_sl.is_safelisted(host):
                    continue

                if not host in hosts:
                    hosts.append(host)

        return results
