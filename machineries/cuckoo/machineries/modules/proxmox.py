import threading

from cuckoo.common import machines
from cuckoo.common.config import cfg

from .. import errors
from ..abstracts import Machinery

try:
    import proxmoxer
    _HAVE_PROXMOXER = True
except ImportError:
    _HAVE_PROXMOXER = False

class Proxmox(Machinery):
    name = "proxmox"

    def init(self):
        breakpoint()

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
        breakpoint()

