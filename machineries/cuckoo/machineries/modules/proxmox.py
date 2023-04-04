import threading

from cuckoo.common import machines
from cuckoo.common.config import cfg

from .. import errors
from ..abstracts import Machinery

try:
    from proxmoxer import ProxmoxAPI
    _HAVE_PROXMOXER = True
except ImportError:
    _HAVE_PROXMOXER = False

class Proxmox(Machinery):
    name = "proxmox"

    def init(self):
        self.dsn = cfg("proxmox.yaml", "dsn", subpkg="machineries")
        self.user = cfg("proxmox.yaml", "user", subpkg="machineries")
        self.pw = cfg("proxmox.yaml", "pw", subpkg="machineries")
        self.vms = {}

    def restore_start(self, machine):
        breakpoint()

    def norestore_start(self, machine):
        breakpoint()

    def stop(self, machine):
        breakpoint()

    def acpi_stop(self, machine):
        breakpoint()

    def state(self, machine):
        breakpoint()

    def dump_memory(self, machine, path):
        breakpoint()

    def handle_paused(self, machine):
        breakpoint()

    def version(self):
        breakpoint()

    @staticmethod
    def verify_dependencies():
        if not _HAVE_PROXMOXER:
            raise errors.MachineryDependencyError(
                    "Python package 'proxmoxer' is not installed. "
                    "To install it, the following python dependency must also be "
                    "installed: 'pip install proxmoxer'"
                    )

