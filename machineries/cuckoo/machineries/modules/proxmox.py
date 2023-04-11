from dataclasses import dataclass

from cuckoo.common import machines
from cuckoo.common.config import cfg
from cuckoo.common.log import CuckooGlobalLogger

from .. import errors
from ..abstracts import Machinery

try:
    from proxmoxer import ProxmoxAPI
    _HAVE_PROXMOXER = True
except ImportError:
    _HAVE_PROXMOXER = False

log = CuckooGlobalLogger(__name__)

class Proxmox(Machinery):
    name = "proxmox"

    def init(self):
        self.dsn = cfg("proxmox.yaml", "dsn", subpkg="machineries")
        self.user = cfg("proxmox.yaml", "user", subpkg="machineries")
        self.pw = cfg("proxmox.yaml", "pw", subpkg="machineries")
        self.vms = {}

    def load_machines(self):
        """Get all IDs needed to control the VMs and check config problems"""
        log.debug(f"Starting to load Proxmox VMs")
        super().load_machines()
        for machine in self.list_machines():
            log.debug(f"loading {machine.label}")
            vm_id, vm_node = self._get_vm_info(machine.label)
            self.vms[machine.label] = _VM(vm_id, vm_node)
            if machine.snapshot is None:
                log.debug(f"no snapshot was given tyting to load first snapshot in list")
                prox = self._create_proxmoxer_connection()
                tmp = prox.nodes(vm_node).qemu(vm_id).snapshot.get()
                if tmp is None:
                    raise errors.MachineryConnectionError(
                            f"A problem occurred while getting the snapshot of {machine.label}"
                            )
                # There is always an extra "you are here" element in the list
                elif len(tmp) <= 1:
                    raise errors.MachineNotFoundError(
                            f"The Machine {machine.label} has no snapshots"
                            )
                machine.snapshot = tmp[0]["name"]

    def restore_start(self, machine):
        state = self.state(machine)
        if state != machines.States.POWEROFF:
            raise errors.MachineUnexpectedStateError(
                    f"Failed to start machine. Expected state 'poweroff'. "
                    f"Actual state: {state}"
                    )

        if not machine.snapshot:
            raise errors.MachineNotFoundError(
                    f"While restore_start of {machine.label}."
                    f"Didn't found snapshot. "
                    f"This should never happen."
                    )

        vm = self.vms.get(machine.label)
        if vm is None:
            raise errors.MachineNotFoundError(
                    f"while restore_start of {machine.label}. "
                    f"Couldn't map label to ID"
                    )

        log.debug(f"Starting analysis machine {machine.label}")
        prox = self._create_proxmoxer_connection()
        prox.nodes(vm.node_name).qemu(vm.vm_id)\
                .snapshot(machine.snapshot).rollback.post()

        while self.state(machine) != machines.States.RUNNING:
            log.debug(f"Waiting for {machine.label} to restore snapshot {machine.snapshot}...")

        log.info(f"restore_start from {machine.label} completed.")

    def norestore_start(self, machine):
        raise NotImplemented

    def stop(self, machine):
        state = self.state(machine)
        if state == machines.States.POWEROFF:
            raise errors.MachineUnexpectedStateError(
                    f"VM {machine.label} is already powered off."
                    )

        vm = self.vms.get(machine.label)
        if vm is None:
            raise errors.MachineNotFoundError(
                    f"While stopping vm {machine.label}: "
                    f"Couldn't find in vms list."
                    )

        log.debug(f"Attempting to stop {machine.label}")
        prox = self._create_proxmoxer_connection()
        prox.nodes(vm.node_name).qemu(vm.vm_id).status.stop.post()

        while self.state(machine) != machines.States.POWEROFF:
            log.debug(f"Waiting for {machine.label} to stop...")
        log.debug(f"{machine.label} was stopped")

    def acpi_stop(self, machine):
        raise NotImplemented

    def state(self, machine):
        vm = self.vms.get(machine.label)
        if vm is None:
            raise errors.MachineNotFoundError(
                    f"While getting the state of {machine.label} "
                    f"the machine wasn't found in the VMs list."
                    )

        log.debug(f"Determine state of {machine.label}")
        prox = self._create_proxmoxer_connection()
        current_status = prox.nodes(vm.node_name).qemu(vm.vm_id)\
                .status.current.get()
        if current_status is None:
            raise errors.MachineryConnectionError(
                    f"Error while getting status of {machine.label} "
                    f"response was None"
                    )
        if current_status.get("qmpstatus") is None:
            raise errors.MachineUnexpectedStateError(
                    f"Error While getting qmpstatus of {machine.label} "
                    f"qmpstatus is None"
                    )

        state = statemapping.get(current_status["qmpstatus"])
        if state is None:
            raise errors.MachineUnexpectedStateError(
                    f"Error while getting qmpstatus of {machine.label} "
                    f"qmpstatus doesn't match with machinery state"
                    )

        log.debug(f"{machine.label} has state: {state}")

        return state

    def dump_memory(self, machine, path):
        raise NotImplemented

    def handle_paused(self, machine):
        raise NotImplemented

    def version(self):
        raise NotImplemented

    def _create_proxmoxer_connection(self):
        log.debug(f"Attempting to connect to Proxmox server in {self.dsn}")
        tmp = ProxmoxAPI(self.dsn, user=self.user, password=self.pw,
                          verify_ssl=False)
        if tmp is None:
            raise errors.MachineryConnectionError(
                    f"Couldn't connect to Proxmox."
                    )
        return tmp

    def _get_vm_info(self, name):
        """
        Get vm_id and node_name by iterating through all nodes and searching for the name.
        Wont stop on first occurence, instead it will try to detect ambiguity
        and if it does it will raise an exception.
        """
        log.debug(f"Attempting to get vmid and node name from {name}")
        prox = self._create_proxmoxer_connection()

        vm_id = 0
        vm_node = ""
        nodes = prox.nodes.get()
        if nodes is None:
            raise errors.MachineryConnectionError(
                    f"Cloudn't get Node list from Proxmox server."
                    )
        elif len(nodes) <= 0:
            raise errors.MachineNotFoundError(
                    f"No Nodes found while loading Machines Info"
                    )
        for node in nodes:
            node_name = node["node"]
            vm_list = prox.nodes(node_name).qemu.get()
            if vm_list is None:
                raise errors.MachineryConnectionError(
                        f"Couldn't get VMs from Proxmox node {node_name}"
                        )
            for vm in vm_list:
                vm_name = vm.get("name")
                if vm_name == name:
                    if vm_node != "":
                        raise errors.MachineUnexpectedStateError(
                                f"Two VMs have the same name {vm_name}"
                                )
                    vm_id = vm["vmid"]
                    vm_node = node_name

        if vm_id == 0:
            raise errors.MachineNotFoundError(
                    f"Cloudn't find a vm with {name} as name"
                    )
        else:
            return vm_id, vm_node

    @staticmethod
    def verify_dependencies():
        log.debug(f"Checking if Proxmoxer is installed...")
        if not _HAVE_PROXMOXER:
            raise errors.MachineryDependencyError(
                    "Python package 'proxmoxer' is not installed. "
                    "To install it, the following python dependency must also be "
                    "installed: 'pip install proxmoxer'"
                    )


@dataclass
class _VM:
    vm_id: int
    node_name: str

    def __init__(self, vm_id, node_name):
        self.vm_id = vm_id
        self.node_name = node_name

statemapping = {
        # Transforms qmpstatus to a Machinery state
        "running": machines.States.RUNNING,
        "paused": machines.States.PAUSED,
        "stopped": machines.States.POWEROFF,
        }

