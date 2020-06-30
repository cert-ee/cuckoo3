# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.


try:
    import libvirt
    _HAVE_LIBVIRT = True
except ImportError:
    _HAVE_LIBVIRT = False

import threading

from cuckoo.common.config import cfg

from ..abstracts import Machinery
from ..helpers import MachineStates
from .. import errors

class LibvirtConn:

    _conns = {}

    @classmethod
    def _open_conn(cls, dsn):
        threadconns = cls._conns.setdefault(threading.get_ident(), {})
        try:
            conn = libvirt.open(dsn)
        except libvirt.libvirtError as e:
            raise errors.MachineryConnectionError(
                f"Failed to connect to hypervisor. Error: {e}"
            )

        threadconns[dsn] = conn
        return conn

    @classmethod
    def _close_conn(cls, dsn):
        threadconns = cls._conns.get(threading.get_ident(), {})
        conn = threadconns.pop(dsn)

        try:
            conn.close()
        except libvirt.libvirtError as e:
            raise errors.MachineryConnectionError(
                f"Failed to close connection to hypervisor. Error {e}"
            )

    @classmethod
    def _get_conn(cls, dsn):
        threadconns = cls._conns.get(threading.get_ident(), {})
        return threadconns.get(dsn)

    @classmethod
    def inject_connection(cls, libvirt_machinery_func):
        def _wrapper(*args):
            dsn = args[0].dsn
            existing = cls._get_conn(dsn)
            try:
                if existing:
                    conn = existing
                else:
                    conn = cls._open_conn(dsn)

                ret = libvirt_machinery_func(*args, conn=conn)
                return ret
            finally:
                if not existing:
                    cls._close_conn(dsn)

        return _wrapper


statemapping = {
    libvirt.VIR_DOMAIN_RUNNING: MachineStates.RUNNING,
    libvirt.VIR_DOMAIN_SHUTOFF: MachineStates.POWEROFF,
    libvirt.VIR_DOMAIN_SHUTDOWN: MachineStates.STOPPING,
    libvirt.VIR_DOMAIN_PAUSED: MachineStates.PAUSED
}

class Libvirt(Machinery):

    def init(self):
        self.dsn = ""
        self.vms = {}

    def load_machines(self):
        super().load_machines()
        for machine in self.list_machines():
            vm = self._get_vm(machine.label)
            self.vms[machine.label] = vm

    @LibvirtConn.inject_connection
    def _get_vm(self, label, conn):
        vm = self.vms.get(label)
        if vm:
            return vm

        try:
            vm = conn.lookupByName(label)
        except libvirt.libvirtError as e:
            raise errors.MachineNotFoundError(
                f"Machine with label {label} not found. Error: {e}"
            )

        return vm

    @LibvirtConn.inject_connection
    def _get_current_snapshot(self, machine, conn):
        libvirt_vm = self._get_vm(machine.label)

        try:
            if libvirt_vm.hasCurrentSnapshot():
                return libvirt_vm.snapshotCurrent()

        except libvirt.libvirtError as e:
            raise errors.MachineryError(
                f"Error retrieving libvirt current snapshot: "
                f"{e.get_error_code()} {e.get_error_message()}"
            )

        raise errors.MachineryError(
            f"Libvirt machine {machine.label} has no current snapshot"
        )

    @LibvirtConn.inject_connection
    def _get_named_snapshot(self, machine, conn):
        libvirt_vm = self._get_vm(machine.label)

        try:
            return libvirt_vm.snapshotLookupByName(machine.snapshot)
        except libvirt.libvirtError as e:
            raise errors.MachineryError(
                f"Failed retrieving named snapshot: "
                f"{e.get_error_code()} {e.get_error_message()}"
            )

    @LibvirtConn.inject_connection
    def restore_start(self, machine, conn):
        state = self.state(machine)
        if state != MachineStates.POWEROFF:
            raise errors.MachineUnexpectedStateError(
                f"Failed to start machine. Expected state 'poweroff'. "
                f"Actual state: {state}"
            )

        if machine.snapshot:
            snapshot = self._get_named_snapshot(machine)
        else:
            snapshot = self._get_current_snapshot(machine)

        libvirt_vm = self._get_vm(machine.label)
        try:
            libvirt_vm.revertToSnapshot(snapshot)
        except libvirt.libvirtError as e:
            raise errors.MachineryError(
                f"Failed to restore snapshot of machine {machine.name}. "
                f"{e.get_error_code()} {e.get_error_message()}"
            )

    @LibvirtConn.inject_connection
    def stop(self, machine, conn):
        state = self.state(machine)
        if state == MachineStates.POWEROFF:
            raise errors.MachineStateReachedError(
                f"Failed to stop machine. Machine already stopped. "
                f"state: {state}"
            )

        libvirt_vm = self._get_vm(machine.label)
        try:
            libvirt_vm.destroy()
        except libvirt.libvirtError as e:
            raise errors.MachineryError(
                f"Failed to stop machine {machine.name}. "
                f"{e.get_error_code()} {e.get_error_message()}"
            )

    @LibvirtConn.inject_connection
    def acpi_stop(self, machine, conn):
        state = self.state(machine)
        if state == MachineStates.POWEROFF:
            raise errors.MachineStateReachedError(
                f"Failed to send ACPI stop to machine. Machine already "
                f"stopped. State: {state}"
            )

        libvirt_vm = self._get_vm(machine.label)
        try:
            libvirt_vm.shutdown()
        except libvirt.libvirtError as e:
            raise errors.MachineryError(
                f"Failed to send ACPI stop to machine {machine.name}. "
                f"{e.get_error_code()} {e.get_error_message()}"
            )

    @LibvirtConn.inject_connection
    def state(self, machine, conn):
        libvirt_vm = self._get_vm(machine.label)

        try:
            state = libvirt_vm.state()
        except libvirt.libvirtError as e:
            raise errors.MachineryError(
                f"Error getting vm state for {machine.label}. "
                f"{e.get_error_code()} {e.get_error_message()}"
            )

        # The first argument in the returned list is the current VM state.
        curr_state, reason = state
        normalized_state = statemapping.get(curr_state)
        if not normalized_state:
            err = f"Unknown/unhandled vm state {curr_state}"
            machine.add_error(err)
            raise errors.MachineryUnhandledStateError(err)

        # The machine may be paused if making a memory dump. No other pausing
        # is used or handled.
        if normalized_state == MachineStates.PAUSED and \
                reason != libvirt.VIR_DOMAIN_PAUSED_DUMP:
            err = f"Unexpected machine paused state"
            machine.add_error(err)
            raise errors.MachineryUnhandledStateError(err)

        return normalized_state

    def dump_memory(self, machine, path):
        # TODO implement this. There are some issues with libvirt creating
        # a memory dump as the root user and group. Causing the file to not
        # be readable. With some tricks it can be made readable, but still
        # cannot be removed. Look into a way to properly solve this before
        # using the workaround.
        pass

    @staticmethod
    def verify_dependencies():
        if not _HAVE_LIBVIRT:
            raise errors.MachineryDependencyError(
                "Python package 'libvirt-python' is not installed. "
                "To install it the following system package must also be "
                "installed: 'libvirt-dev'"
            )

class KVM(Libvirt):
    name = "kvm"

    def init(self):
        super().init()
        self.dsn = cfg("kvm.yaml", "dsn", subpkg="machineries")
