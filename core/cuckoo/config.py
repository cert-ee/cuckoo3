# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import config

class Machinery(config.String):

    _MACHINERY_CACHE = []

    def _fill_cache(self):
        from cuckoo.common.packages import enumerate_plugins
        from cuckoo.machineries.abstracts import Machinery

        modules = enumerate_plugins(
            "cuckoo.machineries.modules", globals(), Machinery
        )
        self._MACHINERY_CACHE = filter(None, [m.name.lower() for m in modules])

    def constraints(self, value):
        super().constraints(value)
        if not self._MACHINERY_CACHE:
            self._fill_cache()

        if value.lower() not in self._MACHINERY_CACHE:
            raise config.ConstraintViolationError(
                f"Machinery module '{value}' does not exist."
            )

typeloaders = {
    "cuckoo.yaml": {
        "machineries": config.List(Machinery, ["kvm"]),
        "resultserver": {
            "listen_ip": config.String(default_val="192.168.122.1"),
            "listen_port": config.Int(default_val=2042, min_value=1024)
        }
    }
}
