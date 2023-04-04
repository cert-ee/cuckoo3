# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
from re import compile, IGNORECASE

from cuckoo.common import config

class MACAddress(config.String):

    _FORMAT = compile(r"^([0-9a-f]{2}:){5}([0-9a-f]{2})$", IGNORECASE)

    def constraints(self, value):
        super().constraints(value)
        if not self._FORMAT.fullmatch(value):
            raise config.ConstraintViolationError(
                f"MAC address format must be in colon notation, example: "
                f"FF:FF:FF:FF:FF:FF. Got: {value}"
            )

exclude_autoload = []
typeloaders = {
    "proxmox.yaml": {
        "dsn": config.String(default_val="xxx.xxx.xxx.xxx"),
        "interface": config.NetworkInterface(
            default_val="eno1", must_be_up=False
        ),
        "machines": config.NestedDictionary("example1", {
                "label": config.String(default_val="example1"),
                "ip": config.String(default_val="192.168.1.101"),
                "platform": config.String(
                    default_val="windows", to_lower=True
                ),
                "os_version": config.String(default_val="10"),
                "mac_address": MACAddress(allow_empty=True, to_lower=True,
                                          required=False),
                "snapshot": config.String(allow_empty=True, required=False),
                "interface": config.NetworkInterface(
                    allow_empty=True, must_be_up=False, must_exist=False,
                    required=False
                ),
                "agent_port": config.Int(
                    default_val=8000, required=False, min_value=1,
                    max_value=2**16-1
                ),
                "architecture": config.String(
                    default_val="amd64", to_lower=True
                ),
                "tags": config.List(
                    config.String, ["exampletag1", "exampletag2"],
                    allow_empty=True
                )
        })
    },
    "kvm.yaml": {
        "dsn": config.String(default_val="qemu:///system"),
        "interface": config.NetworkInterface(
            default_val="virbr0", must_be_up=False
        ),
        "machines": config.NestedDictionary("example1", {
                "label": config.String(default_val="example1"),
                "ip": config.String(default_val="192.168.122.101"),
                "platform": config.String(
                    default_val="windows", to_lower=True
                ),
                "os_version": config.String(default_val="10"),
                "mac_address": MACAddress(allow_empty=True, to_lower=True,
                                          required=False),
                "snapshot": config.String(allow_empty=True, required=False),
                "interface": config.NetworkInterface(
                    allow_empty=True, must_be_up=False, must_exist=False,
                    required=False
                ),
                "agent_port": config.Int(
                    default_val=8000, required=False, min_value=1,
                    max_value=2**16-1
                ),
                "architecture": config.String(
                    default_val="amd64", to_lower=True
                ),
                "tags": config.List(
                    config.String, ["exampletag1", "exampletag2"],
                    allow_empty=True
                )
        })
    },
    "qemu.yaml": {
        "interface": config.NetworkInterface(
            default_val="br0", must_exist=True, must_be_up=False
        ),
        "disposable_copy_dir": config.DirectoryPath(
            allow_empty=True, must_exist=True, writable=True
        ),
        "binaries": {
            "qemu_img": config.FilePath(
                "/usr/bin/qemu-img", readable=True, executable=True
            ),
            "qemu_system_x86_64": config.FilePath(
                default_val="/usr/bin/qemu-system-x86_64", readable=True,
                executable=True
            )
        },
        "machines": config.NestedDictionary("example1", {
                "qcow2_path": config.FilePath(default_val="/home/cuckoo/.vmcloak/vms/qemu/win10_1/disk.qcow2", readable=True),
                "snapshot_path": config.FilePath(default_val="/home/cuckoo/.vmcloak/vms/qemu/win10_1/memory.snapshot", readable=True),
                "machineinfo_path": config.FilePath("/home/cuckoo/.vmcloak/vms/qemu/win10_1/machineinfo.json", readable=True),
                "ip": config.String(default_val="192.168.30.101"),
                "mac_address": MACAddress(to_lower=True, allow_empty=True,
                                          required=False),
                "platform": config.String(
                    default_val="windows", to_lower=True
                ),
                "os_version": config.String(default_val="10"),
                "architecture": config.String(
                    default_val="amd64", to_lower=True
                ),
                "interface": config.NetworkInterface(
                    allow_empty=True, must_exist=True, must_be_up=False,
                    required=False
                ),
                "agent_port": config.Int(
                    default_val=8000, required=False, min_value=1,
                    max_value=2**16-1
                ),
                "tags": config.List(
                    config.String, ["exampletag1", "exampletag2"],
                    allow_empty=True
                )
        })
    }
}
