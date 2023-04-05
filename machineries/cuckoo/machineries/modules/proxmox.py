import threading

from dataclasses import dataclass

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

    def load_machines(self):
        """Get all IDs needed to control the VMs and check config problems"""
        super().load_machines()
        for machine in self.list_machines():
            vm_id, vm_node = self._get_vm_info(machine.label)
            self.vms[machine.label] = _VM(vm_id, vm_node)
            if machine.snapshot is None:
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
        breakpoint()

    def norestore_start(self, machine):
        breakpoint()

    def stop(self, machine):
        breakpoint()

    def acpi_stop(self, machine):
        breakpoint()

    def state(self, machine):
        vm = self.vms.get(machine.label)
        if vm is None:
            raise errors.MachineNotFoundError(
                    f"While getting the state of {machine.label} "
                    f"the machine wasn't found in the VMs list."
                    )

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

        return state

    def dump_memory(self, machine, path):
        breakpoint()

    def handle_paused(self, machine):
        breakpoint()

    def version(self):
        breakpoint()

    def _create_proxmoxer_connection(self):
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

