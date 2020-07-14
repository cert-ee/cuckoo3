# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import config

typeloaders = {
    "kvm.yaml": {
        "dsn": config.String(default_val="qemu:///system"),
        "interface": config.String(default_val="virbr0"),
        "machines": config.NestedDictionary("example1", {
                "label": config.String(default_val="example1"),
                "ip": config.String(default_val="192.168.122.101"),
                "platform": config.String(default_val="windows"),
                "os_version": config.String(default_val="10"),
                "mac_address": config.String(allow_empty=True),
                "snapshot": config.String(allow_empty=True),
                "interface": config.String(allow_empty=True),
                "tags": config.List(
                    config.String, ["exampletag1", "exampletag2", "dank"]
                )
        })
    }
}
