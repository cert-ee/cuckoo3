# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.config import cfg
from cuckoo.common import machines
from cuckoo.common.netcapture import TCPDump, NetworkCaptureError
from cuckoo.common.log import CuckooGlobalLogger

from . import errors

log = CuckooGlobalLogger(__name__)

class Machinery:
    name = ""

    def __init__(self, cfg):
        self.cfg = cfg
        self.machines = []
        self.netcaptures = {}

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

    def start_netcapture(self, machine, pcap_path, ignore_ip_ports=[]):
        if machine.interface:
            capture_interface = machine.interface
        elif self.cfg["interface"]:
            capture_interface = self.cfg["interface"]
        else:
            raise errors.MachineNetCaptureError(
                f"Cannot start network capture for machine: {machine.name}. "
                f"No machine or machinery ({machine.machinery_name}) "
                f"interface has been configured."
            )

        tcpdump_path = cfg("cuckoo", "tcpdump", "path")
        netcapture = TCPDump(pcap_path, capture_interface, tcpdump_path)
        netcapture.capture_host(machine.ip)

        for ip, port in ignore_ip_ports:
            netcapture.ignore_ip_port(ip, port)

        try:
            netcapture.start()
        except NetworkCaptureError as e:
            raise errors.MachineNetCaptureError(
                f"Failed to start network capture for machine {machine.name}: "
                f"{e}"
            )

        self.netcaptures[machine.name] = netcapture

    def stop_netcapture(self, machine):
        netcapture = self.netcaptures.get(machine.name)
        if not netcapture:
            return

        try:
            netcapture.stop()
        except NetworkCaptureError as e:
            raise errors.MachineNetCaptureError(str(e))

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

        for netcapture in self.netcaptures.values():
            try:
                netcapture.stop()
            except Exception as e:
                log.error("Error while stopping network capture", error=e)

    def version(self):
        """Return the string version of the virtualization software."""
        return ""

    @staticmethod
    def verify_dependencies():
        pass
