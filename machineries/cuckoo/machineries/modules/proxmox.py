import threading

from cuckoo.common import machines
from cuckoo.common import cfg

from .. import errors
from ..abstracts import Machinery

try:
    import proxmoxer
    _HAVE_PROXMOXER = True
except ImportError:
    _HAVE_PROXMOXER = False

class Proxmox(Machinery):
    def init(self):
        pass

    def restore_start(self, machine):
        pass

    def norestore_start(self, machine):
        pass

    def stop(self, machine):
        pass

    def acpi_stop(self, machine):
        pass

    def state(self, machine):
        pass

    def dump_memory(self, machine, path):
        pass

    def handle_paused(self, machine):
        pass

    def version(self):
        pass

    @staticmethod
    def verify_dependencies():
        pass

