# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import logging
import os
from dpkt import http as dpkthttp
from httpreplay import (
    reader, protohandlers, udpprotoparsers, transport, protoparsers,
    guess
)

from cuckoo.common import safelist
from cuckoo.common.log import set_logger_level, CuckooGlobalLogger
from cuckoo.common.storage import TaskPaths, Paths
from cuckoo.processing.errors import PluginError, DisablePluginError
from cuckoo.processing.signatures.pattern import (
    PatternScanner, PatternSignatureError
)
from cuckoo.processing.signatures.signature import IOC

from ..abtracts import Processor

set_logger_level("httpreplay.transport", logging.ERROR)
set_logger_level("httpreplay.protoparsers", logging.ERROR)

log = CuckooGlobalLogger(__name__)

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
        if not TaskPaths.pcap(self.ctx.task.id).is_file():
            raise DisablePluginError("No PCAP available")

        self.ip_sl.clear_temp()

        tls_secrets = self.ctx.network.tls.sessions
        self.tcp_handlers = {
            25: protohandlers.smtp_handler,
            80: protohandlers.http_handler,
            443: lambda: protohandlers.https_handler(tls_secrets),
            465: protohandlers.smtp_handler,
            587: protohandlers.smtp_handler,
            8000: protohandlers.http_handler,
            8080: protohandlers.http_handler,
            "generic": lambda: guess.tcp_guessprotocol(tls_secrets)
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
        data = {
            "request": {},
            "response": {}
        }
        for httpdata in (sent, recv):
            if not httpdata:
                continue

            if isinstance(httpdata, dpkthttp.Request):
                data["request"] = self._make_http_request(
                     dst, protocol, httpdata
                )
            elif isinstance(httpdata, dpkthttp.Response):
                data["response"] = self._make_http_response(
                    protocol, httpdata
                )

        if not data.get("request") and not data.get("response"):
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
            "srcport": srcport,
            "tx_size": 0 if not sent else len(sent),
            "rx_size": 0 if not recv else len(recv)
        }

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
        if not pcap_path.is_file():
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

                if host not in hosts:
                    hosts.append(host)

        return results


class NetworkPatternSignatures(Processor):

    @classmethod
    def enabled(cls):
        return len(os.listdir(Paths.pattern_signatures("network"))) > 0

    @classmethod
    def init_once(cls):
        cls.scanner = None
        # Read all network pattern signature yml files.
        networksigs_dir = Paths.pattern_signatures("network")
        if not networksigs_dir.is_dir():
            return

        for sigfile in os.listdir(networksigs_dir):
            if not sigfile.endswith((".yml", ".yaml")):
                continue

            sigfile_path = os.path.join(networksigs_dir, sigfile)
            log.debug("Loading network signature file", filepath=sigfile_path)
            if not cls.scanner:
                cls.scanner = PatternScanner()

            try:
                cls.scanner.load_sigfile(sigfile_path)
            except (ValueError, TypeError,
                    KeyError, PatternSignatureError) as e:
                raise PluginError(
                    f"Failed to load network signature file: {sigfile_path}. "
                    f"Error: {e}"
                ).with_traceback(e.__traceback__)

        if not cls.scanner:
            return

        # Ask the scanner to compile the loaded patterns into a hyperscan
        # database. It is so possible to show what regex caused the compile
        # error, as this information is not made available by Hyperscan.
        try:
            cls.scanner.compile()
        except PatternSignatureError as e:
            raise PluginError(
                "Failed to compile network signatures. Invalid hyperscan "
                f"regex in one of the signatures. Hyperscan error: {e}"
            )

    def init(self):
        if not self.scanner:
            raise DisablePluginError("No network pattern signature scanner")

        self.match_tracker = self.scanner.new_tracker()

    def _scan_http(self):
        network = self.ctx.result.get("network", {})
        for http in network.get("http", []):
            request = http.get("request", {})
            response = http.get("response", {})

            url = request.get("url")
            if url:
                self.scanner.scan(
                    scan_str=url, orig_str=url, event=None,
                    event_kind="http_url", processing_ctx=self.ctx
                )

            for header in request.get("headers", []):
                combined = f"{header['key']}: {header['value']}"
                self.scanner.scan(
                    scan_str=combined, orig_str=combined, event=None,
                    event_kind="http_header", event_subtype="request",
                    processing_ctx=self.ctx
                )

            for header in response.get("headers", []):
                combined = f"{header['key']}: {header['value']}"
                self.scanner.scan(
                    scan_str=combined, orig_str=combined, event=None,
                    event_kind="http_header", event_subtype="response",
                    processing_ctx=self.ctx
                )

    def _scan_smtp(self):
        network = self.ctx.result.get("network", {})

        for smtp in network.get("smtp", []):
            request = smtp.get("request", {})

            hostname = request.get("hostname")
            if hostname:
                self.scanner.scan(
                    scan_str=hostname, orig_str=hostname, event=None,
                    event_kind="smtp_hostname", processing_ctx=self.ctx
                )

            for mailfrom in request.get("mail_from", []):
                self.scanner.scan(
                    scan_str=mailfrom, orig_str=mailfrom, event=None,
                    event_kind="smtp_mailfrom", processing_ctx=self.ctx
                )

            for mailto in request.get("mail_to", []):
                self.scanner.scan(
                    scan_str=mailto, orig_str=mailto, event=None,
                    event_kind="smtp_rcptto", processing_ctx=self.ctx
                )

            for name, value in request.get("headers", {}).items():
                combined = f"{name}: {value}"
                self.scanner.scan(
                    scan_str=combined, orig_str=combined, event=None,
                    event_kind="smtp_header", processing_ctx=self.ctx
                )

            message = request.get("message")
            if message:
                self.scanner.scan(
                    scan_str=message, orig_str=message, event=None,
                    event_kind="smtp_message", processing_ctx=self.ctx
                )

    def _scan_dns(self):
        dns = self.ctx.result.get("network", {}).get("dns", {})

        for q in dns.get("query", []):
            self.scanner.scan(
                scan_str=q["name"], orig_str=q["name"], event=None,
                event_kind="dns_q", event_subtype=q["type"].lower(),
                processing_ctx=self.ctx
            )

        for r in dns.get("response", []):
            self.scanner.scan(
                scan_str=r["data"], orig_str=r["data"], event=None,
                event_kind="dns_r", event_subtype=r["type"].lower(),
                processing_ctx=self.ctx
            )

    def _scan_host(self):
        network = self.ctx.result.get("network", {})
        for host in network.get("host", []):
            self.scanner.scan(
                scan_str=host, orig_str=host, event=None,
                event_kind="ip", processing_ctx=self.ctx
            )

    def start(self):
        if not self.scanner:
            return

        self._scan_http()
        self._scan_smtp()
        self._scan_dns()
        self._scan_host()

        for match in self.match_tracker.get_matches():
            self.ctx.signature_tracker.add_signature(
                name=match.name, short_description=match.short_description,
                description=match.description, score=match.score,
                family=match.family, tags=match.tags, ttps=match.ttps,
                iocs=[IOC(value=matchctx.orig_str) for matchctx in
                      match.get_iocs()]
            )

    def cleanup(self):
        if self.scanner:
            self.scanner.clear()
