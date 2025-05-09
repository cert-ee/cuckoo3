# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import queue
import socket
import subprocess
import threading
from pathlib import Path

from psutil import net_if_stats

from cuckoo.common.ipc import UnixSocketServer, ReaderWriter, IPCError
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.node import ExistingResultServer
from cuckoo.common.route import Routes
from cuckoo.common.strictcontainer import Route
from cuckoo.common.machines import Machine

from .errors import (
    RooterError,
    RouteUnavailableError,
    InterfaceError,
    CommandFailedError,
    RequestFailedError,
    InvalidRequestError,
    ExistingRouteError,
)
from .undoable import UndoableTracker, Undoable
from .vpn import VPNs, OpenVPN

log = CuckooGlobalLogger("rooter")


class NIC:
    """Wrapper around network interfaces. Used to enable/disable forwarding,
    check if interfaces exist, if they are up, etc. Tracks changes made
    per interface. All changes can be undo."""

    NET_PATH = "/proc/sys/net"

    def __init__(self, rooterctx, name):
        # Check if name exceeds max Linux interface name length.
        # Should never really happen, unless a long postfix or high
        # number of interfaces is used by Cuckoo rooter.
        if len(name) > 15:
            raise InterfaceError(
                f"Interface assembled name is larger than 15 characters {name}"
            )

        self.ctx = rooterctx
        self.name = name
        self.undoables = UndoableTracker()

    def is_up(self):
        nic = net_if_stats().get(self.name)
        if not nic:
            return False

        return nic.isup

    def _forwarding_enabled(self, iptype):
        if iptype not in ("ipv4", "ipv6"):
            raise ValueError("iptype must be ipv4 or ipv6")

        path = Path(self.NET_PATH, iptype, "conf", self.name, "forwarding")
        if not path.is_file():
            raise InterfaceError(f"Forwarding file does not exist: {path}")

        try:
            return int(path.read_text())
        except ValueError:
            return False

    def ipv4_forwarding_enabled(self):
        return self._forwarding_enabled("ipv4")

    def ipv6_forwarding_enabled(self):
        return self._forwarding_enabled("ipv6")

    def _write_forwarding(self, iptype, value):
        value = str(value)
        if iptype not in ("ipv4", "ipv6"):
            raise ValueError("iptype must be ipv4 or ipv6")

        if value not in ("1", "0"):
            raise ValueError("Value can be 0 or 1")

        path = Path(self.NET_PATH, iptype, "conf", self.name, "forwarding")
        if not path.is_file():
            raise InterfaceError(f"Forwarding file does not exist: {path}")

        path.write_text(value)

    def enable_ipv4_forwarding(self):
        try:
            undoable = Undoable(
                apply_func=self._write_forwarding,
                apply_args=("ipv4", "1"),
                undo_func=self.disable_ipv4_forwarding,
            )
            self.undoables.append(undoable)
            return undoable
        except InterfaceError as e:
            raise InterfaceError(
                f"Failed to enable ipv4 forwarding on interface: {self.name}. {e}"
            )

    def enable_ipv6_forwarding(self):
        try:
            undoable = Undoable(
                apply_func=self._write_forwarding,
                apply_args=("ipv6", "1"),
                undo_func=self.disable_ipv4_forwarding,
            )
            self.undoables.append(undoable)
            return undoable
        except InterfaceError as e:
            raise InterfaceError(
                f"Failed to enable ipv6 forwarding on interface: {self.name}. {e}"
            )

    def disable_ipv4_forwarding(self):
        try:
            self._write_forwarding("ipv4", "0")
        except InterfaceError:
            # Do not raise an error if the path is missing and forwarding is
            # being disabled. Interface is likely already gone.
            return

    def disable_ipv6_forwarding(self):
        try:
            self._write_forwarding("ipv6", "0")
        except InterfaceError:
            # Do not raise an error if the path is missing and forwarding is
            # being disabled. Interface is likely already gone.
            return

    def drop_forward_default(self):
        undoable = Undoable(
            apply_func=self.ctx.iptables.forward_drop_enable,
            apply_args=self,
            undo_func=self.ctx.iptables.forward_drop_disable,
            undo_args=self,
        )
        self.undoables.append(undoable)
        return undoable

    def undo(self):
        self.undoables.undo_all()

    def release(self):
        self.ctx.interfaces.release_interface(self)

    def __str__(self):
        return self.name


def _run_process(binary_path, argstuple):
    if argstuple:
        if not isinstance(argstuple, tuple):
            command = (binary_path, argstuple)
        else:
            command = (binary_path,) + argstuple
    else:
        command = binary_path

    log.debug("Running process", command=command)
    try:
        subprocess.run(
            command,
            shell=False,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise CommandFailedError(
            f"Error running command {command}. "
            f"Exit code: {e.returncode}. Stderr: {e.stderr}"
        )


class IPRoute2:
    """Wrapper around the ip binary of iproute2."""

    # Note: there is no flushing, this is on purpose.
    # Route caching has been removed in Linux kernel 3.6
    # https://git.kernel.org/pub/scm/linux/kernel/git/netdev/net-next.git
    # /commit/?id=5e9965c15ba88319500284e590733f4a4629a288

    def __init__(self, ip_path):
        self.path = ip_path

    def add_from_rule(self, ip, table_id):
        _run_process(self.path, ("rule", "add", "from", ip, "table", str(table_id)))

    def delete_from_rule(self, ip, table_id):
        _run_process(self.path, ("rule", "del", "from", ip, "table", str(table_id)))


class RoutingTable:
    def __init__(self, rooterctx, table_id):
        self.ctx = rooterctx
        self.id = table_id
        self.undoables = UndoableTracker()

    def add_srcroute(self, ip):
        undoable = Undoable(
            apply_func=self.ctx.ip.add_from_rule,
            apply_args=(ip, self.id),
            undo_func=self._delete_srcsource,
            undo_args=ip,
        )
        self.undoables.append(undoable)

        return undoable

    def _delete_srcsource(self, ip):
        self.ctx.ip.delete_from_rule(ip, self.id)

    def undo(self):
        self.undoables.undo_all()

    def release(self):
        self.ctx.routing_tables.release_table(self)


class IPTables:
    ROOTER_COMMENT = "cuckoo3-rooter"

    def __init__(self, iptables_path):
        self.path = iptables_path

    def _run_iptables(self, *args):
        full_args = args + ("-m", "comment", "--comment", self.ROOTER_COMMENT)
        _run_process(self.path, full_args)

    def forward_enable(self, src_interface, dst_interface, src_ip):
        # Insert rules as first in the chain so that other routes do not
        # influence it/break auto routing.
        self._run_iptables(
            "-I",
            "FORWARD",
            "1",
            "-i",
            src_interface.name,
            "-o",
            dst_interface.name,
            "--source",
            src_ip,
            "-j",
            "ACCEPT",
        )
        self._run_iptables(
            "-I",
            "FORWARD",
            "1",
            "-i",
            dst_interface.name,
            "-o",
            src_interface.name,
            "--destination",
            src_ip,
            "-j",
            "ACCEPT",
        )

    def forward_disable(self, src_interface, dst_interface, src_ip):
        self._run_iptables(
            "-D",
            "FORWARD",
            "-i",
            src_interface.name,
            "-o",
            dst_interface.name,
            "--source",
            src_ip,
            "-j",
            "ACCEPT",
        )
        self._run_iptables(
            "-D",
            "FORWARD",
            "-i",
            dst_interface.name,
            "-o",
            src_interface.name,
            "--destination",
            src_ip,
            "-j",
            "ACCEPT",
        )

    def masquerade_enable(self, src_ip, dst_interface):
        self._run_iptables(
            "-t",
            "nat",
            "-A",
            "POSTROUTING",
            "-s",
            src_ip,
            "-o",
            dst_interface.name,
            "-j",
            "MASQUERADE",
        )

    def masquerade_disable(self, src_ip, dst_interface):
        self._run_iptables(
            "-t",
            "nat",
            "-D",
            "POSTROUTING",
            "-s",
            src_ip,
            "-o",
            dst_interface.name,
            "-j",
            "MASQUERADE",
        )

    def forward_drop_enable(self, interface):
        self._run_iptables("-A", "FORWARD", "-i", interface.name, "-j", "DROP")
        self._run_iptables("-A", "FORWARD", "-o", interface.name, "-j", "DROP")

    def forward_drop_disable(self, interface):
        self._run_iptables("-D", "FORWARD", "-i", interface.name, "-j", "DROP")
        self._run_iptables("-D", "FORWARD", "-o", interface.name, "-j", "DROP")

    def _input_accept_toggle(
        self, action, src_ip, protocol=None, dst_ip=None, dst_port=None
    ):
        args = [action, "INPUT", "-s", src_ip]
        if dst_ip:
            args.extend(["-d", dst_ip])

        if protocol and dst_port:
            args.extend(["-p", protocol, "--dport", str(dst_port)])

        args.extend(["-j", "ACCEPT"])
        self._run_iptables(*args)

    def input_accept_enable(self, src_ip, protocol=None, dst_ip=None, dst_port=None):
        self._input_accept_toggle("-A", src_ip, protocol, dst_ip, dst_port)

    def input_accept_disable(self, src_ip, protocol=None, dst_ip=None, dst_port=None):
        self._input_accept_toggle("-D", src_ip, protocol, dst_ip, dst_port)

    def _output_accept_toggle(
        self, action, dst_ip, protocol=None, src_ip=None, dst_port=None
    ):
        args = [action, "OUTPUT", "-d", dst_ip]
        if src_ip:
            args.extend(["-s", src_ip])

        if protocol and dst_port:
            args.extend(["-p", protocol, "--dport", str(dst_port)])

        args.extend(["-j", "ACCEPT"])
        self._run_iptables(*args)

    def output_accept_enable(self, dst_ip, protocol=None, src_ip=None, dst_port=None):
        self._output_accept_toggle("-A", dst_ip, protocol, src_ip, dst_port)

    def output_accept_disable(self, dst_ip, protocol=None, src_ip=None, dst_port=None):
        self._output_accept_toggle("-D", dst_ip, protocol, src_ip, dst_port)

    def _toggle_input_drop(self, action, src_ip):
        self._run_iptables(action, "INPUT", "-s", src_ip, "-j", "DROP")

    def input_drop_enable(self, src_ip):
        self._toggle_input_drop("-A", src_ip)

    def input_drop_disable(self, src_ip):
        self._toggle_input_drop("-D", src_ip)

    def _toggle_output_drop(self, action, dst_ip):
        self._run_iptables(action, "OUTPUT", "-d", dst_ip, "-j", "DROP")

    def output_drop_enable(self, dst_ip):
        self._toggle_output_drop("-A", dst_ip)

    def output_drop_disable(self, dst_ip):
        self._toggle_output_drop("-D", dst_ip)

    def enable_state_tracking(self, src_ip):
        self._run_iptables(
            "-A",
            "INPUT",
            "-s",
            src_ip,
            "-m",
            "state",
            "--state",
            "ESTABLISHED,RELATED",
            "-j",
            "ACCEPT",
        )
        self._run_iptables(
            "-A",
            "OUTPUT",
            "-d",
            src_ip,
            "-m",
            "state",
            "--state",
            "ESTABLISHED,RELATED",
            "-j",
            "ACCEPT",
        )

    def disable_state_tracking(self, src_ip):
        self._run_iptables(
            "-D",
            "INPUT",
            "-s",
            src_ip,
            "-m",
            "state",
            "--state",
            "ESTABLISHED,RELATED",
            "-j",
            "ACCEPT",
        )
        self._run_iptables(
            "-D",
            "OUTPUT",
            "-d",
            src_ip,
            "-m",
            "state",
            "--state",
            "ESTABLISHED,RELATED",
            "-j",
            "ACCEPT",
        )


class InternetRoute:
    def __init__(self, routing_table, interface):
        self.routing_table = routing_table
        self.interface = interface


class _InterfaceTracker:
    """A tracker for all used (existing and generated) network interface names.
    It guards against duplicate interfaces and ensures performed
    interface actions are always cleaned up."""

    INTERFACE_PREFIX = "cuckoo"

    def __init__(self, rooterctx):
        self.ctx = rooterctx
        self._interfaces = {}
        self._interface_lock = threading.RLock()

    def get_existing_interface(self, name):
        """Get an interface helper for a network interface that is not
        defined by Cuckoo rooter."""
        with self._interface_lock:
            interface = self._interfaces.get(name)
            if not interface:
                interface = NIC(self.ctx, name)
                self._interfaces[name] = interface

            if not interface.is_up():
                raise RooterError(f"Interface {name} does not exist or is not up.")

            return interface

    def new_interface(self, postfix):
        with self._interface_lock:
            ifname = None
            # Limit to arbitrary number of interfaces with a prefix. Rooter
            # should never reach this amount of interfaces unless someone
            # uses 999+ VPNs etc at the same time or interfaces somehow
            # don't get released.
            for c in range(0, 999):
                name = f"{self.INTERFACE_PREFIX}{postfix}{c}"
                if name not in self._interfaces:
                    ifname = name
                    break

            if not ifname:
                raise RooterError(
                    f"Cannot create new interface name. All names are in use."
                )

            interface = NIC(self.ctx, name)
            self._interfaces[name] = interface
            return interface

    def release_interface(self, interface):
        with self._interface_lock:
            # Undo actions stored on interface object that have not
            # been undone before untracking it.
            interface.undo()
            self._interfaces.pop(interface.name, None)

    def undo_all(self):
        with self._interface_lock:
            for interface in list(self._interfaces.values()):
                self.release_interface(interface)


class _RoutingTableTracker:
    """A tracker for all existing and generated routing table ids used.
    It tries to ensure routing tables actions to not interfere with other
    routing tables used by rooter.

    User provided table ids cannot be checked against the routing table range
    if they are the aliases of the routing table ids"""

    def __init__(self, rooterctx, start_range=None, end_range=None):
        if (
            start_range is not None
            and end_range is not None
            and start_range > end_range
        ):
            raise RooterError(
                f"Routing table start_range ({start_range}) must be "
                f"smaller than end_range ({end_range})"
            )

        self.ctx = rooterctx
        self._start = start_range
        self._end = end_range
        self._routing_tables = {}
        self._tables_lock = threading.RLock()

    def range_set(self):
        return self._start is not None and self._end is not None

    def set_range(self, start, end):
        if not isinstance(start, int) or not isinstance(end, int):
            raise TypeError("Start and end range must be integers")

        if start > end:
            raise ValueError(
                f"Routing table start_range ({start}) must be "
                f"smaller than end_range ({end})"
            )

        self._start = start
        self._end = end

    def get_existing_table(self, table_id):
        """Get a routing table helper for a routing table that is not
        defined by Cuckoo rooter."""
        with self._tables_lock:
            # If table id is a table alias, do not convert it to an integer.
            if isinstance(table_id, str) and table_id.isdigit():
                table_id = int(table_id)

            # Check if the given integer table id falls within the reserved
            # Cuckoo auto-create routing table range. This is not allowed.
            if isinstance(table_id, int) and self.range_set():
                if self._start <= table_id <= self._end:
                    raise RooterError(
                        f"Requested existing routing table ({table_id}) "
                        f"falls within Cuckoo rooter auto-create routing "
                        f"table range. These cannot overlap."
                    )

            table = self._routing_tables.get(table_id)
            if not table:
                table = RoutingTable(self.ctx, table_id)
                self._routing_tables[table_id] = table

            return table

    def get_next_table(self):
        """Get the next routing table in the specified range. These tables
        should not exists yet/be used by anything. Cuckoo should be able to
        create and use these."""
        if not self.range_set():
            raise RooterError(
                "No routing table id range is set. Cannot determine new table id."
            )

        with self._tables_lock:
            for table_id in range(self._start, self._end):
                if table_id in self._routing_tables:
                    continue

                table = RoutingTable(self.ctx, table_id)
                self._routing_tables[table_id] = table

                return table

            raise RooterError(
                f"All possible table ids in range: "
                f"{self._start} to {self._end} are in use. "
                f"Cannot create a next table."
            )

    def release_table(self, table):
        with self._tables_lock:
            table.undo()
            self._routing_tables.pop(table.id, None)

    def undo_all(self):
        with self._tables_lock:
            for table in list(self._routing_tables.values()):
                table.undo()


def _enable_forwarding_and_drop(interface):
    # Enables forwarding on an interface and applies iptables rules
    # to drop all incoming/outgoing traffic by default, unless a rule
    # explicitly allow this is added.
    interface.enable_ipv4_forwarding()
    interface.drop_forward_default()


def enable_drop(requestctx):
    """Accept traffic to the result server from source ip and
    accept traffic to source ip on the agent port. Drop all other
    input/output."""
    undoables = UndoableTracker()

    # Accept result server traffic from the source IP
    undoables.append(
        Undoable(
            apply_func=requestctx.ctx.iptables.input_accept_enable,
            apply_args=(
                requestctx.src_ip,
                "tcp",
                requestctx.result_server.listen_ip,
                requestctx.result_server.listen_port,
            ),
            undo_func=requestctx.ctx.iptables.input_accept_disable,
            undo_args=(
                requestctx.src_ip,
                "tcp",
                requestctx.result_server.listen_ip,
                requestctx.result_server.listen_port,
            ),
        )
    )

    # Accept agent traffic going to the source ip.
    undoables.append(
        Undoable(
            apply_func=requestctx.ctx.iptables.output_accept_enable,
            apply_args=(requestctx.src_ip, "tcp", None, requestctx.machine.agent_port),
            undo_func=requestctx.ctx.iptables.output_accept_disable,
            undo_args=(requestctx.src_ip, "tcp", None, requestctx.machine.agent_port),
        )
    )

    # Accept connections that are established from any of the allowed inputs
    undoables.append(
        Undoable(
            apply_func=requestctx.ctx.iptables.enable_state_tracking,
            apply_args=requestctx.src_ip,
            undo_func=requestctx.ctx.iptables.disable_state_tracking,
            undo_args=requestctx.src_ip,
        )
    )

    # Drop all other input/output traffic that is not allowed.
    undoables.append(
        Undoable(
            apply_func=requestctx.ctx.iptables.input_drop_enable,
            apply_args=requestctx.src_ip,
            undo_func=requestctx.ctx.iptables.input_drop_disable,
            undo_args=requestctx.src_ip,
        )
    )
    undoables.append(
        Undoable(
            apply_func=requestctx.ctx.iptables.output_drop_enable,
            apply_args=requestctx.src_ip,
            undo_func=requestctx.ctx.iptables.output_drop_disable,
            undo_args=requestctx.src_ip,
        )
    )

    return undoables


def enable_vpn(requestctx):
    """Drop all traffic (except to resultserver and agent) as a default. Then
    retrieve an existing or start a new a VPN using the options provided.
    Enables forwarding (from and to VPN interface and src interface)
    and masquerading of the source IP on the VPN interface. An IP rule
    is added to the routing table of the VPN."""
    if not requestctx.ctx.vpns.vpns_available:
        raise RequestFailedError("No VPNs available")

    # Apply a drop route before enabling other routes.
    undoables = enable_drop(requestctx)

    rooterctx = requestctx.ctx
    vpn = rooterctx.vpns.get_vpn(requestctx.route.options.get("country"))

    # Enable ipv4 forwarding on the VPN or source interfaces if it is not
    # enabled yet.
    if not vpn.interface.ipv4_forwarding_enabled():
        vpn.interface.enable_ipv4_forwarding()

    if not requestctx.src_interface.ipv4_forwarding_enabled():
        _enable_forwarding_and_drop(requestctx.src_interface)

    # Add the source IP to the routing table of the VPN.
    undoables.append(vpn.routing_table.add_srcroute(requestctx.src_ip))

    # Enable forwarding from and to the source interface to the VPN interface
    # for the given source IP.
    undoables.append(
        Undoable(
            apply_func=rooterctx.iptables.forward_enable,
            apply_args=(requestctx.src_interface, vpn.interface, requestctx.src_ip),
            undo_func=rooterctx.iptables.forward_disable,
            undo_args=(requestctx.src_interface, vpn.interface, requestctx.src_ip),
        )
    )

    # Enable masquerading for the source IP on the VPN interface. So that
    # the VPN interface IP is used for packets going over the VPN.
    undoables.append(
        Undoable(
            apply_func=rooterctx.iptables.masquerade_enable,
            apply_args=(requestctx.src_ip, vpn.interface),
            undo_func=rooterctx.iptables.masquerade_disable,
            undo_args=(requestctx.src_ip, vpn.interface),
        )
    )
    undoables.append(Undoable(undo_func=vpn.decrement_users))
    return undoables


def enable_internet(requestctx):
    """Drop all traffic (except to resultserver and agent) as a default.

    Enables forwarding (from and to 'internet' interface and src interface)
    and masquerading of the source IP on the 'internet' interface. An IP rule
    is added to the routing table of the configured 'internet' interface."""
    if not requestctx.ctx.internet_route:
        raise RequestFailedError("No internet interface and routing table is set")

    # Apply a drop route before enabling other routes.
    undoables = enable_drop(requestctx)
    rooterctx = requestctx.ctx

    # Enable ipv4 forwarding on the internet or source interfaces if it is not
    # enabled yet.
    if not rooterctx.internet_route.interface.ipv4_forwarding_enabled():
        rooterctx.internet_route.interface.enable_ipv4_forwarding()

    if not requestctx.src_interface.ipv4_forwarding_enabled():
        _enable_forwarding_and_drop(requestctx.src_interface)

    # Add the source IP to the preconfigured routing table of the
    # 'internet' routing table.
    undoables.append(
        rooterctx.internet_route.routing_table.add_srcroute(requestctx.src_ip)
    )

    # Enable forwarding from and to the source interface to the
    # internet/dirty line interface for the given source IP.
    undoables.append(
        Undoable(
            apply_func=rooterctx.iptables.forward_enable,
            apply_args=(
                requestctx.src_interface,
                rooterctx.internet_route.interface,
                requestctx.src_ip,
            ),
            undo_func=rooterctx.iptables.forward_disable,
            undo_args=(
                requestctx.src_interface,
                rooterctx.internet_route.interface,
                requestctx.src_ip,
            ),
        )
    )

    # Enable masquerading for the source IP on the internet interface. So that
    # the internet interface IP is used for packets and replies
    # can be received.
    undoables.append(
        Undoable(
            apply_func=rooterctx.iptables.masquerade_enable,
            apply_args=(requestctx.src_ip, rooterctx.internet_route.interface),
            undo_func=rooterctx.iptables.masquerade_disable,
            undo_args=(requestctx.src_ip, rooterctx.internet_route.interface),
        )
    )

    return undoables


class RequestContext:
    """A wrapper for a new routing request. Holds all information needed
    so a worker can process the request."""

    def __init__(
        self, rooterctx, route_dict, machine_dict, result_server_dict, readerwriter
    ):
        self.ctx = rooterctx

        try:
            self.machine = Machine.from_dict(machine_dict)
            self.route = Route(**route_dict)
            self.result_server = ExistingResultServer.from_dict(result_server_dict)
        except (TypeError, KeyError, ValueError) as e:
            raise InvalidRequestError(
                f"Invalid machine, route or result server dict: {e}"
            )

        self.handler = rooterctx.get_route_handler(self.route.type)
        self.src_interface = rooterctx.interfaces.get_existing_interface(
            self.machine.interface
        )
        self.readerwriter = readerwriter

        # These IDs are mapped to requests. The request will be denied
        # if the ID already exists.
        self.id = self.src_ip

        self._undoables = None
        self._undone = False
        self._route_lock = threading.Lock()

    @property
    def src_ip(self):
        return self.machine.ip

    def route_applied(self):
        return self._undoables is not None

    def map_enabled_route(self):
        self.ctx.add_enabled_route(self)

    def unmap_enabled_route(self):
        self.ctx.undo_enabled_route(self.readerwriter.sock)

    def apply_route(self):
        with self._route_lock:
            # Only apply route if undone was not called before. This can happen
            # if lots of routes are queued and a requester cancels it.
            if self._undone:
                log.warning(
                    "Route undone before it was applied. Not applying route",
                    src_ip=self.src_ip,
                    type=self.route.type,
                )
                return

            self._undoables = self.handler(self)

    def undo(self):
        with self._route_lock:
            self._undone = True
            if not self._undoables:
                return

            self._undoables.undo_all()

    def __str__(self):
        return f"<RequestContext src_ip={self.src_ip}, route={self.route}>"


class RooterContext:
    """A container that holds all shared objects needed by rooter, workers,
    requests, and other. It also holds all applied routes. Undo_all must
    always be called when stopping rooter."""

    route_handlers = {
        "vpn": enable_vpn,
        "internet": enable_internet,
        "drop": enable_drop,
    }

    def __init__(self, iptables_path, ip_path, rooterlogs_path, openvpn_path=None):
        self.iptables = IPTables(iptables_path)
        self.ip = IPRoute2(ip_path)
        self.openvpn = OpenVPN(openvpn_path)
        self.vpns = VPNs()
        self.routing_tables = _RoutingTableTracker(self)
        self.interfaces = _InterfaceTracker(self)
        self.logpath = Path(rooterlogs_path)

        self.internet_route = None
        self._available_routes = set()
        self._enabled_routes_lock = threading.RLock()
        self._enabled_routes = {}

        self.add_available_route("drop")

    def add_available_route(self, route):
        if route not in self.route_handlers:
            raise RooterError(f"Unsupported route type {route}")

        self._available_routes.add(route)

    def add_internet_route(self, routing_table, interface):
        self.internet_route = InternetRoute(
            routing_table=self.routing_tables.get_existing_table(routing_table),
            interface=self.interfaces.get_existing_interface(interface),
        )
        self.add_available_route("internet")

    def available_routes_dict(self):
        return Routes(
            available=self._available_routes, vpn_countries=self.vpns.countries
        ).to_dict()

    def get_route_handler(self, route_type):
        if route_type not in self._available_routes:
            raise RouteUnavailableError(f"Route type {route_type} not available")

        handler = self.route_handlers.get(route_type)
        if not handler:
            raise RouteUnavailableError(f"Route type {route_type} is not supported")

        return handler

    def add_enabled_route(self, requestctx):
        with self._enabled_routes_lock:
            if self.srcip_route_exists(requestctx):
                raise ExistingRouteError(
                    f"A route already exists for source ip: {requestctx.src_ip}"
                )
            self._enabled_routes[requestctx.readerwriter.sock] = requestctx

    def undo_enabled_route(self, sock):
        with self._enabled_routes_lock:
            requestctx = self._enabled_routes.pop(sock, None)
            if not requestctx:
                return

            log.info("Undoing routes", src_ip=requestctx.src_ip, route=requestctx.route)
            requestctx.undo()

    def srcip_route_exists(self, requestctx):
        with self._enabled_routes_lock:
            for existing in self._enabled_routes.values():
                if existing.src_ip == requestctx.src_ip:
                    return True

            return False

    def undo_all(self):
        with self._enabled_routes_lock:
            for sock in list(self._enabled_routes.keys()):
                try:
                    self.undo_enabled_route(sock)
                except Exception as e:
                    log.exception(
                        "Fatal error cleaning up routes. It is recommended to "
                        "check if any remaining iptables rules exist.",
                        error=e,
                    )

        self.routing_tables.undo_all()
        self.interfaces.undo_all()
        self.vpns.stop_all()


class _RooterResponses:
    @staticmethod
    def success(error=""):
        return {"success": True, "error": error}

    @staticmethod
    def fail(error):
        return {"success": False, "error": error}


class RooterWorker(threading.Thread):
    """Worker thread that runs the actual functions stored in RequestContexts
    that apply requested routes."""

    def __init__(self, rooter):
        super().__init__()
        self.rooter = rooter

        self.do_run = True

    def run(self):
        log.debug("Worker starting")
        while self.do_run:
            try:
                requestctcx = self.rooter.work_queue.get(timeout=1)
            except queue.Empty:
                continue

            log.debug("Performing requested route", work=requestctcx)
            try:
                requestctcx.apply_route()
                log.info(
                    "Route request completed",
                    src_ip=requestctcx.src_ip,
                    route=requestctcx.route,
                )
            except RouteUnavailableError as e:
                log.warning("Failed to apply route", error=e)
                self.rooter.queue_response(
                    requestctcx.readerwriter, _RooterResponses.fail(str(e)), close=False
                )
            except RooterError as e:
                log.error(
                    "Failed to apply request route",
                    type=requestctcx.route.type,
                    options=requestctcx.route.options,
                    src_ip=requestctcx.src_ip,
                    src_interface=requestctcx.src_interface,
                    error=e,
                )
                self.rooter.queue_response(
                    requestctcx.readerwriter,
                    _RooterResponses.fail(
                        "Failed to apply route. See rooter logs for details."
                    ),
                    close=False,
                )
            else:
                self.rooter.queue_response(
                    requestctcx.readerwriter, _RooterResponses.success(), close=False
                )
            finally:
                if not requestctcx.route_applied():
                    requestctcx.unmap_enabled_route()

    def stop(self):
        self.do_run = False


class Rooter(UnixSocketServer):
    """The rooter unix socket server. Accepts commands and queues the work
    for it or performs it immediately."""

    NUM_ROOTER_WORKERS = 1

    def __init__(self, sock_path, rooterctx):
        super().__init__(sock_path)

        self.ctx = rooterctx
        self.work_queue = queue.Queue()
        self.response_queue = queue.Queue()

        self.subject_handler = {
            "getroutes": self._get_routes,
            "enableroute": self._enable_route,
            "disableroute": self._disable_route,
        }
        self.workers = []

    def _get_routes(self, msg, readerwriter):
        self._send_response(readerwriter, self.ctx.available_routes_dict(), close=True)

    def _enable_route(self, msg, readerwriter):
        args = msg.get("args", {})
        if not args or not set(args.keys()).issubset(
            {"machine", "route", "resultserver"}
        ):
            raise KeyError("Missing one or more arguments")

        try:
            requestctx = RequestContext(
                self.ctx,
                route_dict=args["route"],
                machine_dict=args["machine"],
                result_server_dict=args["resultserver"],
                readerwriter=readerwriter,
            )
        except (RouteUnavailableError, InvalidRequestError) as e:
            log.debug("Cannot complete route request", msg=msg, error=e)
            self._send_response(readerwriter, _RooterResponses.fail(str(e)), close=True)

        else:
            log.info(
                "New route request", src_ip=requestctx.src_ip, route=requestctx.route
            )
            try:
                requestctx.map_enabled_route()
                self.work_queue.put(requestctx)
            except ExistingRouteError as e:
                log.warning(
                    "Cannot complete route request", requestctx=requestctx, error=e
                )
                self._send_response(
                    readerwriter, _RooterResponses.fail(str(e)), close=True
                )
                return

    def _disable_route(self, msg, readerwriter):
        """Undo a route when it is requested by the connected client."""
        self.ctx.undo_enabled_route(readerwriter.sock)

    def queue_response(self, readerwriter, response, close=False):
        self.response_queue.put((readerwriter, response, close))

    def _send_response(self, readerwriter, response, close=False):
        try:
            readerwriter.send_json_message(response)
        except socket.error as e:
            log.debug("Failed to send response.", error=e)
            close = True

        if close:
            self.untrack(readerwriter.sock)

    def timeout_action(self):
        while not self.response_queue.empty():
            try:
                rw_resp_close = self.response_queue.get(block=False)
            except queue.Empty:
                break

            self._send_response(*rw_resp_close)

    def post_disconnect_cleanup(self, sock):
        """Undo a route if the requesting client closes the connection"""
        self.ctx.undo_enabled_route(sock)

    def handle_connection(self, sock, addr):
        log.debug("New client connection")
        self.track(sock, ReaderWriter(sock))

    def handle_message(self, sock, msg):
        log.debug("New message", message=msg)
        subject = msg.get("subject")

        if not subject:
            return

        readerwriter = self.socks_readers[sock]
        handler = self.subject_handler.get(subject)
        if not handler:
            log.debug("Unsupported subject", msg=msg)
            self._send_response(
                readerwriter, _RooterResponses.fail("Unsupported subject"), close=True
            )
            return

        try:
            handler(msg, readerwriter)
        except (TypeError, KeyError) as e:
            log.warning("Incorrect message received", msg=repr(msg), error=e)
            self._send_response(readerwriter, _RooterResponses.fail(str(e)), close=True)
        except RooterError as e:
            log.error("Error handling message", msg=repr(msg), error=e)
            self._send_response(
                readerwriter,
                _RooterResponses.fail(
                    "Unexpected rooter error. Cannot complete request. "
                    "See rooter logs for details."
                ),
                close=True,
            )
        except Exception as e:
            log.exception("Fatal error while handling message", msg=repr(msg), error=e)
            raise

    def stop(self):
        log.info("Stopping rooter")
        if not self.do_run:
            return

        super().stop()
        for worker in self.workers:
            worker.stop()

        self.cleanup()

    def start(self, socket_group=None):
        log.info("Starting rooter")
        for _ in range(self.NUM_ROOTER_WORKERS):
            worker = RooterWorker(self)
            self.workers.append(worker)
            worker.start()

        try:
            self.create_socket(owner_group=socket_group)
        except IPCError as e:
            raise RooterError(f"Failed to create socket. {e}")

        log.info("Ready to accept messages")
        self.start_accepting(timeout=1)
