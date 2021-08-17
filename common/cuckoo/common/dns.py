# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

class ResolveTracker:

    def __init__(self):
        self._ip_map = {}
        self._domain_map = {}

    def find_domains(self, ip):
        return list(self._domain_map.get(ip, set()))

    def find_ips(self, domain):
        return list(self._ip_map.get(domain, set()))

    def find_domain_all(self, domain):
        all_domains = set()
        for entry in self._domain_map.keys():
            if entry.endswith(domain):
                all_domains.add(entry)

        return list(all_domains)

    def add_resolved(self, domain, ip):
        self._domain_map.setdefault(domain, set()).add(ip)
        self._ip_map.setdefault(ip, set()).add(domain)
