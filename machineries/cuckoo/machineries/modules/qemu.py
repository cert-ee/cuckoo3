# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import subprocess
import time
from pathlib import Path
from re import search
from shutil import which
from threading import RLock

from pkg_resources import parse_version

from cuckoo.common import machines
from cuckoo.common.ipc import UnixSockClient, IPCError, timeout_read_response
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.storage import UnixSocketPaths, File, delete_file

from .. import errors
from ..abstracts import Machinery

log = CuckooGlobalLogger(__name__)

class QMPError(Exception):
    pass

class QMPClient:
    """A simple QEMU Machine Protocol client to send commands and request
    states."""

    def __init__(self, qmp_sockpath):
        self._sockpath = qmp_sockpath

        self._client_obj = None
        # Lock should be kept when writing and reading. This prevents
        # another thread (y) from sending a command while another (x) is
        # reading. This would cause the message for thread y to be ignored/lost
        # when x is reading.
        self._lock = RLock()

    @property
    def _client(self):
        with self._lock:
            if not self._client_obj:
                self.connect()

            return self._client_obj

    def execute(self, command, args_dict=None):
        with self._lock:
            try:
                self._client.send_json_message({
                    "execute": command,
                    "arguments": args_dict or {}
                })
            except IPCError as e:
                raise QMPError(
                    f"Failed to send command to QMP socket. "
                    f"Command: {command}, args: {args_dict}. {e}"
                )

    def read(self, timeout=60):
        with self._lock:
            try:
                return timeout_read_response(self._client, timeout=timeout)
            except IPCError as e:
                raise QMPError(
                    f"Failed to read response from QMP socket. {e}"
                )

    def wait_read_return(self, timeout=60):
        with self._lock:
            start = time.monotonic()
            while True:
                mes = self.read(timeout=timeout)
                # Skip all messages that do not have the return key.
                ret = mes.get("return")
                if ret:
                    return ret

                if time.monotonic() - start >= timeout:
                    raise QMPError("Timeout waiting for return")

    def query_status(self):
        with self._lock:
            self.execute("query-status")
            return self.wait_read_return()["status"]

    def connect(self):
        # Connect and perform 'capabilities handshake'. Must be performed
        # before any commands can be sent.
        with self._lock:
            self._client_obj = UnixSockClient(self._sockpath)
            self._client_obj.connect(maxtries=1, timeout=20)
            try:
                res = timeout_read_response(self._client_obj, timeout=60)
            except IPCError as e:
                raise QMPError(
                    f"Failure while waiting for QMP connection header. {e}"
                )

            if not res.get("QMP"):
                raise QMPError(
                    f"Unexpected QMP connection header. Header: {res}"
                )

            self.execute("qmp_capabilities")

    def close(self):
        self._client.cleanup()

class _QEMUMachine:
    """Helper object that can hold the qemu process, attributes that don't
    belong on the Machine object, etc."""

    def __init__(self, machine, cpus, ramsize, use_kvm, disposables_dir,
                 qmp_sockpath):
        self.machine = machine
        self.cpus = cpus
        self.ramsize = ramsize
        self.use_kvm = use_kvm
        self.disposables_dir = disposables_dir
        self.qmp_sockpath = qmp_sockpath
        self.qcow2_path = machine.label
        self.snapshot_path = machine.snapshot

        self.snapshot_compression = None
        self.snapshot_compressed = True
        self.process = None
        self.qmp = None

        self._lock = RLock()

    def snapshot_determine_compression(self):
        ftype = File(self.snapshot_path).type.lower()
        if "lz4" in ftype:
            self.snapshot_compression = "lz4"
        elif "gzip" in ftype:
            self.snapshot_compression = "gzip"
        elif "qemu suspend" in ftype:
            self.snapshot_compressed = False

    def kill_process(self, timeout=60):
        with self._lock:
            if not self.process_running():
                return

            self.process.kill()
            try:
                _, stderr = self.process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                raise errors.MachineryError(
                    "Failed to read stderr after sending SIGKILL to process. "
                    "Waited maximum time. QEMU process might still be "
                    f"running. Machine: {self.machine.name}. "
                    f"PID: {self.process.pid}"
                )

            return stderr.decode()

    def process_running(self):
        with self._lock:
            if not self.process:
                return False

            if self.process.poll() is None:
                return True

            return False

    def set_qemu_process(self, process, qmp_client):
        with self._lock:
            if self.process or self.qmp:
                raise errors.MachineryError(
                    "Cannot set qemu process, a process still exists. "
                    "This must first be cleared."
                )

            self.process = process
            self.qmp = qmp_client

    def clean(self):
        with self._lock:
            if self.process_running():
                self.kill_process()

            if self.qmp_sockpath.exists():
                delete_file(self.qmp_sockpath)

            self.process = None
            if self.qmp:
                self.qmp.close()

            self.qmp = None

_MIN_QEMU_VERSION = parse_version("2.11")

_start_commands = {
    "windows": {
        "amd64": {
            "default_version": parse_version("4.1"),
            "versions": {
                parse_version("2.11"): [
                    "%EMULATOR_BINARY%",
                    "-M", "q35",
                    "-nodefaults",
                    "-vga", "std",
                    "-rtc", "base=localtime,driftfix=slew",
                    "-realtime", "mlock=off",
                    "-m", "%RAMSIZE%", "-smp", "%CPUS%",
                    "-netdev", "type=tap,ifname=%INTERFACE%,script=no,downscript=no,id=net0",
                    "-device", "rtl8139,netdev=net0,mac=%MAC_ADDRESS%,bus=pcie.0,addr=3",
                    "-drive", "file=%DISPOSABLE_DISK_PATH%,format=qcow2,if=none,id=disk",
                    "-device", "ich9-ahci,id=ahci",
                    "-device", "ide-drive,bus=ahci.0,unit=0,drive=disk,bootindex=2",
                    "-drive", "if=none,id=cdrom,readonly=on",
                    "-device", "ide-cd,bus=ahci.1,unit=0,drive=cdrom,bootindex=1",
                    "-device", "usb-ehci,id=ehci",
                    "-device", "usb-tablet,bus=ehci.0",
                    "-soundhw", "hda",
                ],
                # From 4.1 the -realtime mlock=off and -device ide-drive
                # are deprecated and those are removed in higher versions.
                parse_version("4.1"): [
                    "%EMULATOR_BINARY%",
                    "-M", "q35",
                    "-nodefaults",
                    "-vga", "std",
                    "-rtc", "base=localtime,driftfix=slew",
                    "-overcommit", "mem-lock=off",
                    "-m", "%RAMSIZE%", "-smp", "%CPUS%",
                    "-netdev", "type=tap,ifname=%INTERFACE%,script=no,downscript=no,id=net0",
                    "-device", "rtl8139,netdev=net0,mac=%MAC_ADDRESS%,bus=pcie.0,addr=3",
                    "-drive", "file=%DISPOSABLE_DISK_PATH%,format=qcow2,if=none,id=disk",
                    "-device", "ich9-ahci,id=ahci",
                    "-device", "ide-hd,bus=ahci.0,unit=0,drive=disk,bootindex=2",
                    "-drive", "if=none,id=cdrom,readonly=on",
                    "-device", "ide-cd,bus=ahci.1,unit=0,drive=cdrom,bootindex=1",
                    "-device", "usb-ehci,id=ehci",
                    "-device", "usb-tablet,bus=ehci.0",
                    "-soundhw", "hda",
                ],
            }
        }
    }
}

_DECOMPRESS_BINARIES = {
    "lz4": which("lz4"),
    "gzip": which("gzip")
}

_DECOMPRESS_COMMANDS = {
    "lz4": "%BINARY_PATH% -c -d < %SNAPSHOT_PATH%",
    "gzip": "%BINARY_PATH% -c -d < %SNAPSHOT_PATH%"
}

def _find_command(qemu_version, platform_architecture_dict):
    selected = None
    if qemu_version:
        for version in sorted(
                platform_architecture_dict["versions"].keys(), reverse=True
        ):
            if qemu_version >= version:
                selected = version
                break

    if not selected:
        if "default" not in platform_architecture_dict:
            return []

        selected = platform_architecture_dict["default"]

    return platform_architecture_dict["versions"][selected]

def _make_command(qemu_machine, emulator_path, disposable_disk_path,
                  emulator_version):

    # Find a dictionary containing the correct qemu vm start arguments for
    # platform and architecture combination.
    plat_arch_dict = _start_commands.get(
        qemu_machine.machine.platform, {}).get(
        qemu_machine.machine.architecture
    )
    if not plat_arch_dict:
        raise errors.MachineryError(
            f"No QEMU startup command found for the combination of "
            f"platform {qemu_machine.machine.platform} and "
            f"architecture: '{qemu_machine.machine.architecture}'."
        )

    command = _find_command(emulator_version, plat_arch_dict)
    if not command:
        raise errors.MachineryError(
            f"No QEMU startup command found for the combination of "
            f"platform {qemu_machine.machine.platform} and "
            f"architecture: '{qemu_machine.machine.architecture}'."
        )

    # Map of placeholders in the command to their value.
    lookup = {
        "%EMULATOR_BINARY%": emulator_path,
        "%RAMSIZE%": qemu_machine.ramsize,
        "%CPUS%": qemu_machine.cpus,
        "%INTERFACE%": qemu_machine.machine.interface,
        "%MAC_ADDRESS%": qemu_machine.machine.mac_address,
        "%DISPOSABLE_DISK_PATH%": disposable_disk_path
    }

    def _do_replace(value):
        if not isinstance(value, str):
            value = str(value)

        for k, v in lookup.items():
            if k in value:
                value = value.replace(k, str(v))

        return value

    command = list(map(_do_replace, command))
    if qemu_machine.use_kvm:
        command.append("-enable-kvm")

    # The QMP unix socket is what the QMP client connects to and uses to
    # send commands and request states of a VM. Each qemu vm process has
    # its own socket.
    command.extend(
        ["-qmp", f"unix:{qemu_machine.qmp_sockpath},server,nowait",
         "-monitor", "none"]
    )
    # The memory snapshot might be compressed. See if the compressed was
    # recognized and we can decompress it. Create a command that results
    # in the decompressed memory being fed to the qemu -incoming argument.
    if qemu_machine.snapshot_compressed:
        compress_type = qemu_machine.snapshot_compression
        binary = _DECOMPRESS_BINARIES.get(compress_type)
        decompress_args = _DECOMPRESS_COMMANDS.get(compress_type)
        if not binary or not decompress_args:
            raise errors.MachineryError(
                f"Cannot build qemu start command. Unknown snapshot "
                f"compression type: {compress_type}. No decompression "
                f"binary or command found."
            )

        decompress_args = decompress_args.replace(
            "%BINARY_PATH%", binary).replace(
            "%SNAPSHOT_PATH%", qemu_machine.snapshot_path
        )
        # Feed the command to decompress the snapshot path to the incoming
        # argument so qemu can decompress it.
        command.extend(["-incoming", f"exec:{decompress_args}"])
    else:
        # Tell qemu how to read uncompressed snapshot path.
        command.extend(
            ["-incoming", f"exec:/bin/cat < {qemu_machine.snapshot_path}"]
        )

    return command



statemapping = {
    "inmigrate": machines.States.STARTING,
    "postmigrate": machines.States.PAUSED,
    "paused": machines.States.PAUSED,
    "running": machines.States.RUNNING
}


class QEMU(Machinery):

    name = "qemu"

    def init(self):
        self.vms = {}
        self.emulator_binaries = {
            "amd64": self.cfg["binaries"]["qemu_system_x86_64"]
        }

        self.qemu_version = self.version()
        if not self.qemu_version:
            log.error(
                "Could not determine QEMU version. This may result in this "
                "machinery module to not function properly"
            )
            return

        if self.qemu_version < _MIN_QEMU_VERSION:
            raise errors.MachineryError(
                f"The minimum QEMU version is: {_MIN_QEMU_VERSION}. "
                f"Detected version: {self.qemu_version}"
            )

    def load_machines(self):
        existing = {}
        for name, values in self.cfg["machines"].items():
            for k in ("ip", "qcow2_path", "snapshot_path",
                      "mac_address", "interface"):
                existing_k = existing.setdefault(k, [])
                k_val = values[k]
                if k_val in existing_k:
                    raise errors.MachineryError(
                        f"Cannot load machine '{name}'. The value for '{k}' "
                        f"is already in use for another machine. "
                        f"This must be unique for each machine."
                    )
                existing_k.append(k_val)

            # Use the qcow2 image path as the disposable disk copy directory
            # if no directory was provided.
            disposables_dir = self.cfg["disposable_copy_dir"] or \
                              str(Path(values["qcow2_path"]).parent)

            # Check if we can read and write to the directory that will be
            # used to make disposable disk copies.
            if not os.access(disposables_dir, os.R_OK) and \
                    os.access(disposables_dir, os.W_OK):

                raise errors.MachineryError(
                    f"The directory used for disposable copies of the "
                    f"qcow2_path is not readable and writable."
                    f"Path: {disposables_dir}."
                )

            if values["platform"] not in _start_commands:
                raise errors.MachineryError(
                    f"Machine '{name}' with platform '{values['platform']}' is "
                    f"not supported. Supported platforms: "
                    f"{list(_start_commands.keys())}"
                )

            if values["architecture"] not in self.emulator_binaries:
                raise errors.MachineryError(
                    f"Machine '{name}' CPU architecture "
                    f"({values['architecture']}) not supported. Supported "
                    f"architectures: {list(self.emulator_binaries.keys())}"
                )

            machine = self._make_machine(name, values)
            qemu_machine = _QEMUMachine(
                machine=machine, cpus=values["cpus"],
                ramsize=values["ramsize"], use_kvm=values["use_kvm"],
                disposables_dir=disposables_dir,
                qmp_sockpath=UnixSocketPaths.machinery_socket(
                    self.name, machine.name
                )
            )
            qemu_machine.snapshot_determine_compression()
            if qemu_machine.snapshot_compressed:
                compress_type = qemu_machine.snapshot_compression
                if not compress_type:
                    raise errors.MachineryError(
                        f"QEMU memory snapshot of machine '{name}' is of "
                        f"unknown filetype or compressed with unsupported "
                        f"compression. Snapshot can be uncompressed or "
                        f"compressed with lz4 or gzip."
                    )

                if not _DECOMPRESS_BINARIES.get(compress_type):
                    raise errors.MachineryError(
                        f"Memory snapshot of machine '{name}' is compressed "
                        f"with '{compress_type}'. But the "
                        f"binary path for this compression was not found. "
                        f"Install it or store the snapshot uncompressed."
                    )

            self.machines.append(machine)
            self.vms[machine.name] = qemu_machine

    def _get_vm(self, name):
        vm = self.vms.get(name)
        if not vm:
            raise errors.MachineNotFoundError(
                f"Machine with name {name} does not exist."
            )

        return vm

    def _make_machine(self, name, values):
        return machines.Machine(
            name=name, label=values["qcow2_path"], ip=values["ip"],
            platform=values["platform"], os_version=values["os_version"],
            tags=values["tags"], snapshot=values["snapshot_path"],
            architecture=values["architecture"],
            interface=values["interface"] or self.cfg.get("interface"),
            agent_port=values["agent_port"],
            mac_address=values["mac_address"], machinery=self
        )

    def state(self, machine):
        vm = self._get_vm(machine.name)
        if not vm.process_running():
            return machines.States.POWEROFF

        try:
            qemu_state = vm.qmp.query_status()
        except QMPError as e:
            # The QMP error only matters is the machine process is still
            # running. If it is not, we know the state is poweroff.
            if not vm.process_running():
                return machines.States.POWEROFF

            raise errors.MachineryError(
                f"Failed to retrieve state for machine '{machine.name}'. "
                f"QMP communication error: {e}"
            )

        normalized_state = statemapping.get(qemu_state)
        if not normalized_state:
            err = f"Unknown/unhandled vm state: '{qemu_state}'"
            machine.add_error(err)
            raise errors.MachineryUnhandledStateError(err)

        return normalized_state

    def _make_disposable_disk(self, vm):
        """Make a new 'disposable' disk, which is a new disk with the machine
        qcow2 disk as a backing disk. A new one must be created for each machine
        start/restore."""
        path = Path(vm.disposables_dir, f"{vm.machine.name}_disposable.qcow2")
        command = [
            self.cfg["binaries"]["qemu_img"],
            "create", "-f", "qcow2",
            "-o", "lazy_refcounts=on,cluster_size=2M",
            "-b", vm.qcow2_path,
            str(path)
        ]
        try:
            subprocess.run(
                command, shell=False, stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL, check=True
            )
        except subprocess.CalledProcessError as e:
            raise errors.MachineryError(
                f"Failed to create disposable disk with qemu-img. "
                f"Command: {command}. Exit code: {e.returncode}. "
                f"Stderr: {e.stderr}"
            )

        return path

    def restore_start(self, machine):
        """Start a new vm with a copy of the machine qcow2 disk and restore
        it to a usable state with using the machine memory snapshot file."""
        state = self.state(machine)
        if state != machines.States.POWEROFF:
            raise errors.MachineUnexpectedStateError(
                f"Cannot start machine. Expected machine to be in state "
                f"{machines.States.POWEROFF}. Actual state: '{state}'."
            )

        vm = self._get_vm(machine.name)
        # Clean kills a remaining qemu process if it was never killed, removes
        # an existing qmp unix sock path, and clears the previous qmp client
        # and qemu process. The stop method also calls this, but in case this
        # failed or was not used, call it to be sure.
        vm.clean()
        emulator_binary = self.emulator_binaries[vm.machine.architecture]

        # Build the command to start a new qemu vm with the binary for the
        # machine architecture. This command results in a started machine
        # restored to the state of the memory snapshot.
        start_command = _make_command(
            qemu_machine=vm, emulator_path=emulator_binary,
            disposable_disk_path=self._make_disposable_disk(vm),
            emulator_version=self.version(path=emulator_binary)
        )

        log.debug(
            "Starting machine with command", machine=machine.name,
            command=start_command
        )
        try:
            proc = subprocess.Popen(
                start_command, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except OSError as e:
            raise errors.MachineryError(
                f"Failed to run start command for machine '{machine.name}'. "
                f"Error: {e}. Command: {start_command}"
            )

        vm.set_qemu_process(proc, QMPClient(vm.qmp_sockpath))
        # Wait a short while until the socket path exists. We do this so
        # the state can be polled after this without waiting for the socket
        # then. We also do this to check if the process does not immediately
        # exit for some reason.
        tries = 0
        while True:
            if tries >= 5:
                break

            if proc.poll() is not None:
                _, stderr = proc.communicate()
                raise errors.MachineryError(
                    f"Failed to start machine '{machine.name}'. QEMU process "
                    f"exited unexpectedly with code {proc.poll()}. "
                    f"Stderr: {stderr}."
                )

            if vm.qmp_sockpath.exists():
                try:
                    vm.qmp.connect()
                except QMPError as e:
                    raise errors.MachineryError(
                        f"Failed to connect to QMP unix socket of machine "
                        f"'{machine.name}'. Error: {e}"
                    )
                break

            tries += 1
            time.sleep(1)

    def stop(self, machine):
        """Stop the qemu vm by sending a quit command. Sends sigkill if
        the process has not exited after a few seconds."""
        state = self.state(machine)
        if state == machines.States.POWEROFF:
            raise errors.MachineStateReachedError(
                "Failed to stop machine. Machine already stopped. "
                f"State: {state}"
            )

        vm = self._get_vm(machine.name)
        qmp_success = False
        do_kill = False
        try:
            # Tell qemu to resume the machine that is paused/stopped.
            vm.qmp.execute("quit")
            qmp_success = True
        except QMPError:
            do_kill = True

        # Wait a few seconds for the process to exit after the quit command.
        # if it has not exited, send a sigkill to the process.
        if qmp_success and vm.process_running():
            tries = 0
            while True:
                if tries >= 2:
                    do_kill = True
                    break

                if not vm.process_running():
                    break

                tries += 1
                time.sleep(1)

        if do_kill:
            stderr = vm.kill_process()
            if stderr:
                log.warning(
                    "Machine has stderr output", machine=machine.name,
                    stderr=stderr
                )

        # Remove process reference and qmp client.
        vm.clean()

    def handle_paused(self, machine):
        """Memory snapshots should be made when the VM is paused. This means
        restoring the snapshot will result in a VM in the paused/stopped state.
        This method sends a continue command to the qmp socket of the qemu
        process."""
        vm = self._get_vm(machine.name)
        try:
            # Tell qemu to resume the machine that is paused/stopped.
            vm.qmp.execute("cont")
        except QMPError as e:
            raise errors.MachineryError(
                f"Failed resume machine '{machine.name}' error sending 'cont' "
                f"command to QMP socket. Error: {e}"
            )

    def version(self, path=None):
        """Get the QEMU version of the specified binary.
        Uses the qemu_system-x86_64 binary if none is given. Returns a
        version object from pkg_resources.parse_version if a version is found.
        Returns an empty string if no version could be determined."""
        if not path:
            path = self.cfg["binaries"]["qemu_system_x86_64"]
        try:
            stdout = subprocess.run(
                [path, "--version"],
                shell=False, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE, check=True
            ).stdout
        except subprocess.CalledProcessError as e:
            raise errors.MachineryError(
                f"Failed to run version command. "
                f"Exit code: {e.returncode}. Stderr: {e.stderr}"
            )

        # Read QEMU version as if it were semver. It is not, but looks similar.
        version_r = (
            br"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*"
            br"[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-]"
            br"[0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
        )

        match = search(version_r, stdout)
        if not match:
            return ""

        return parse_version(match.group().strip().decode())
