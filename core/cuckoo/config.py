# Copyright (C) 2019-2023 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from secrets import token_hex

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


exclude_autoload = ["distributed.yaml"]
typeloaders = {
    "cuckoo.yaml": {
        "machineries": config.List(Machinery, value=["qemu"]),
        "resultserver": {
            "listen_ip": config.String(default_val="192.168.30.101"),
            "listen_port": config.Int(default_val=2042, min_value=1024)
        },
        "tcpdump": {
            "enabled": config.Boolean(default_val=True),
            "path": config.FilePath(
                default_val="/usr/sbin/tcpdump", must_exist=True
            )
        },
        "network_routing": {
            "enabled": config.Boolean(default_val=False),
            "rooter_socket": config.UnixSocketPath(
                must_exist=True, readable=True, writable=True
            ),
        },
        "platform": {
            "autotag": config.Boolean(default_val=False)
        },
        "state_control": {
            "cancel_unidentified": config.Boolean(default_val=False)
        },
        "processing": {
            "worker_amount": {
                "identification": config.Int(default_val=1, min_value=1),
                "pre": config.Int(default_val=1, min_value=1),
                "post": config.Int(default_val=1, min_value=1),
            }
        },
        "remote_storage": {
            "api_url": config.HTTPUrl(allow_empty=True),
            "api_key": config.String(sensitive=True, allow_empty=True)
        },
        "submit": {
            "min_file_size" : config.Int(default_val=133, min_value=1),
            "max_file_size" : config.Int(default_val=4294967296, min_value=1)
        },
    },
    "distributed.yaml": {
        "remote_nodes": config.NestedDictionary("example1", {
            "api_url": config.HTTPUrl(default_val="http://127.0.0.1:8090"),
            "api_key": config.String(sensitive=True, default_val="examplekey"),
        }),
        "node_settings": {
            "api_key": config.String(sensitive=True, default_val=token_hex(32))
        }
    },
    "analysissettings.yaml": {
        "default": {
            "timeout": config.Int(default_val=120, min_value=1),
            "priority": config.Int(default_val=1, min_value=1),
            "route": {
                "type": config.String(allow_empty=True),
                "options": config.Dict(
                    element_class=config.String, default_val={},
                    allow_empty=True
                )
            }
        },
        "platform": {
            "versions": config.Dict(
                config.List(config.String), default_val={
                    "windows": ["10"]
                }
            ),
            "multi_platform": config.List(
                config.String, default_val=["windows"]
            ),
            "fallback_platforms": config.List(
                config.String, default_val=["windows"]
            )
        },
        "limits": {
            "max_timeout": config.Int(default_val=300, min_value=1),
            "max_priority": config.Int(default_val=999, min_value=1),
            "max_platforms": config.Int(default_val=3, min_value=1)
        }
    }
}
