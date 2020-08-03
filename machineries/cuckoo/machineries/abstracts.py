# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import machines
from cuckoo.common.log import CuckooGlobalLogger

from . import errors

log = CuckooGlobalLogger(__name__)

class Machinery:
    name = ""

    def __init__(self, cfg):
        self.cfg = cfg
        self.machines = []

    def init(self):
        pass

    def load_machines(self):
        for name, values in self.cfg["machines"].items():
            machine = machines.Machine(
                name=name, label=values["label"], ip=values["ip"],
                platform=values["platform"], os_version=values["os_version"],
                tags=values["tags"], snapshot=values["snapshot"],
                mac_address=values["mac_address"], machinery=self
            )
            self.machines.append(machine)

    def list_machines(self):
        """"List machines defined in the configuration of a machinery. Should
        return a list of machine helper objects"""
        return self.machines

    def restore_start(self, machine):
        raise NotImplementedError

    def norestore_start(self, machine):
        raise NotImplementedError

    def stop(self, machine):
        raise NotImplementedError

    def acpi_stop(self, machine):
        raise NotImplementedError

    def state(self, machine):
        raise NotImplementedError

    def dump_memory(self, machine, path):
        raise NotImplementedError

    def shutdown(self):
        for machine in self.machines:
            try:
                log.info(
                    "Stopping machine.", machinery=self.name,
                    machine=machine.name
                )
                self.stop(machine)
            except errors.MachineStateReachedError:
                # Ignore this error, as it simply means the machine already
                # has the desired stopped state.
                pass
            except errors.MachineryError as e:
                log.error(
                    "Error while stopping machine in machinery shutdown.",
                    machinery=self.name, machine=machine.name, error=e
                )

    def version(self):
        """Return the string version of the virtualization software."""
        return ""

    @staticmethod
    def verify_dependencies():
        pass
