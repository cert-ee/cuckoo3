# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

class Routes:

    def __init__(self, available, vpn_countries=[]):
        self.available = set(r.lower() for r in available)
        self.vpn_countries = set(c.lower() for c in vpn_countries)

    def to_dict(self):
        return {
            "available": list(self.available),
            "vpn": {
                "countries": sorted(self.vpn_countries)
            }
        }

    def merge_routes(self, routes):
        self.available.update(routes.available)
        self.vpn_countries.update(routes.vpn_countries)

    @classmethod
    def from_dict(cls, d):
        return cls(
            available=d["available"], vpn_countries=d["vpn"]["countries"]
        )

    def has_route(self, route):
        if route.type not in self.available:
            return False

        if route.type == "vpn" and route.options.get("country"):
            if route.options.get("country").lower() not in self.vpn_countries:
                return False

        return True
