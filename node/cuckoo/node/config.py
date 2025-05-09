# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common import config
from cuckoo.common.storage import Paths


class VPNPoolVPNType(config.String):
    SUPPORTED_VPNTYPES = ["openvpn"]

    def constraints(self, value):
        super().constraints(value)

        if value.lower() not in self.SUPPORTED_VPNTYPES:
            raise config.ConstraintViolationError(
                f"Unsupported VPN type: '{value}'. Only the following types "
                f"are supported: {self.SUPPORTED_VPNTYPES}"
            )


exclude_autoload = ["routing.yaml"]
typeloaders = {
    "routing.yaml": {
        "internet": {
            "enabled": config.Boolean(default_val=False),
            "interface": config.NetworkInterface(),
            "routing_table": config.String(default_val="main"),
        },
        "vpn": {
            "preconfigured": {
                "enabled": config.Boolean(default_val=False),
                "vpns": config.NestedDictionary(
                    "example_vpn",
                    {
                        "interface": config.NetworkInterface(default_val="tun0"),
                        "routing_table": config.String(default_val="vpn0"),
                        "country": config.String(default_val="country1"),
                    },
                ),
            },
            "vpnpool": {
                "enabled": config.Boolean(default_val=False),
                "routing_tables": {
                    "start_range": config.Int(
                        default_val=100, min_value=1, max_value=2**32 - 1
                    ),
                    "end_range": config.Int(
                        default_val=200, min_value=1, max_value=2**32 - 1
                    ),
                },
                "providers": config.NestedDictionary(
                    "example_provider",
                    {
                        "max_connections": config.Int(default_val=5, min_value=1),
                        "vpns": config.DictList(
                            child_typeloaders={
                                "type": VPNPoolVPNType(),
                                "config_path": config.FilePath(
                                    must_exist=True, readable=True
                                ),
                                "up_script": config.FilePath(
                                    must_exist=True, readable=True, executable=True
                                ),
                                "country": config.String(),
                            },
                            default_val=[
                                {
                                    "path": "example.ovpn",
                                    "type": "openvpn",
                                    "up_script": Paths.rooter_files(
                                        "scripts", "openvpnroutes.sh"
                                    ),
                                    "country": "country1",
                                }
                            ],
                        ),
                    },
                ),
            },
        },
    }
}
