# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import logging
import click

from cuckoo.common.log import exit_error, CuckooGlobalLogger
from cuckoo.common.shutdown import call_registered_shutdowns
from cuckoo.common.startup import StartupError
from cuckoo.common.storage import cuckoocwd
from cuckoo.node.rooter.rooter import RooterError

log = CuckooGlobalLogger(__name__)

def _add_preconfigured_vpns(rooterctx, configuredsettings):
    """Adds all preconfigured VPNs to the vpns tracker of the
    rooter context object"""
    for name, values in configuredsettings["vpns"].items():
        log.debug(
            "Adding preconfigured VPN", name=name,
            routing_table=values["routing_table"],
            interface=values["interface"], country=values["country"]
        )
        rooterctx.vpns.add_preconfigured_vpn(
            rooterctx, routing_table_id=values["routing_table"],
            interface_name=values["interface"], country=values["country"],
            name=name
        )
        rooterctx.add_available_route("vpn")

def _add_autovpn_vpnpool(rooterctx, poolsettings):
    """Adds all vpnproviders and their VPNs to the vpns tracker of the
    rooter context object."""
    from pathlib import Path
    from cuckoo.node.rooter.vpn import VPNProvider
    if not rooterctx.openvpn.path:
        raise StartupError("Cannot enable VPN pool. OpenVPN path not set.")

    if not Path(rooterctx.openvpn.path).is_file():
        raise StartupError(
            f"Cannot enable VPN pool. OpenVPN path does not exist: "
            f"{rooterctx.openvpn.path}"
        )

    rooterctx.routing_tables.set_range(
        start=poolsettings["routing_tables"]["start_range"],
        end=poolsettings["routing_tables"]["end_range"]
    )

    vpns = 0
    for name, settings in poolsettings["providers"].items():
        provider = VPNProvider(
            rooterctx=rooterctx, name=name,
            max_connections=settings["max_connections"]
        )
        for vpn in settings["vpns"]:
            country = vpn["country"]
            config = vpn["config_path"]
            log.debug(
                "Adding VPN pool VPN", provider=name, country=country,
                config=config
            )
            provider.add_available_vpn(
                country=country, vpntype=vpn["type"],
                config_path=config, up_script=vpn["up_script"]
            )
            vpns += 1

        rooterctx.vpns.add_provider(provider)

    if vpns:
        rooterctx.add_available_route("vpn")

def _start_rooter(iptables_path, ip_path, socket_path, openvpn_path=None,
                  socket_group=None, loglevel=logging.DEBUG):
    from cuckoo.common.shutdown import register_shutdown
    from cuckoo.common.startup import init_global_logging
    from cuckoo.common.storage import Paths
    from cuckoo.common.config import cfg, load_config, ConfigurationError
    from cuckoo.node.rooter.rooter import RooterContext, Rooter

    init_global_logging(loglevel, Paths.log("rooter.log"))

    conf_path = Paths.config("routing.yaml", subpkg="node")
    if not conf_path.is_file():
        raise StartupError(f"Configuration file {conf_path} is missing.")

    try:
        load_config(conf_path, subpkg="node")
    except ConfigurationError as e:
        raise StartupError(f"Failed to load config file {conf_path}. {e}")

    logspath = Paths.logpath("rooter")
    if not logspath.exists():
        logspath.mkdir()

    rooterctx = RooterContext(
        iptables_path=iptables_path, ip_path=ip_path,
        rooterlogs_path=logspath, openvpn_path=openvpn_path
    )

    if cfg("routing.yaml", "internet", "enabled", subpkg="node"):
        interface = cfg("routing.yaml", "internet", "interface", subpkg="node")
        routing_table = cfg(
            "routing.yaml", "internet", "routing_table", subpkg="node"
        )
        log.debug(
            "Adding internet route", interface=interface,
            routing_table=routing_table
        )
        rooterctx.add_internet_route(
            routing_table=routing_table, interface=interface
        )

    if cfg("routing.yaml", "vpn", "preconfigured", "enabled", subpkg="node"):
        _add_preconfigured_vpns(
            rooterctx,
            cfg("routing.yaml", "vpn", "preconfigured", subpkg="node")
        )

    if cfg("routing.yaml", "vpn", "vpnpool", "enabled", subpkg="node"):
        _add_autovpn_vpnpool(
            rooterctx, cfg("routing.yaml", "vpn", "vpnpool", subpkg="node")
        )

    log.info(
        "Starting Cuckoo rooter", group=socket_group, socket_path=socket_path
    )
    rooter = Rooter(socket_path, rooterctx)
    register_shutdown(rooter.stop)
    register_shutdown(rooterctx.undo_all)

    rooter.start(socket_group=socket_group)


def _make_rooter_command(cwd, debug, socket, group, iptables, ip, openvpn):
    import sys
    args = [
        sys.argv[0], socket,
        "--cwd", str(cwd),
        "--iptables", iptables,
        "--ip", ip,
        "--openvpn", openvpn
    ]

    if group:
        args.extend(["--group", group])

    if debug:
        args.append("--debug")

    return args

@click.command()
@click.argument("socket", type=click.Path(readable=False, dir_okay=False), default="/tmp/cuckoo3-rooter.sock", required=False)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.option("-d", "--debug", is_flag=True, help="Enable verbose logging")
@click.option("-g", "--group", default="cuckoo", help="Unix socket group")
@click.option("--iptables", type=click.Path(exists=True), default="/sbin/iptables", help="Path to the iptables(8) binary")
@click.option("--ip", type=click.Path(exists=True), default="/sbin/ip", help="Path to the ip(8) binary")
@click.option("--sudo", is_flag=True, help="Request superuser privileges")
@click.option("--sudo-path", type=click.Path(exists=True), default="/usr/bin/sudo", help="Path to the sudo(8) binary")
@click.option("--openvpn", type=click.Path(), default="/usr/sbin/openvpn", help="Path to the OpenVPN(8) binary")
@click.option("--print-command", is_flag=True,
              help="Dry run and print the starting command that can be used in "
                   "things such as systemd or supervisord. Correct arguments/flags should be supplied so command can be generated.")
def main(cwd, debug, socket, group, iptables, ip, sudo, sudo_path,
         openvpn, print_command):
    """A unix socket server that applies and removes requested network routes
     for analysis machines. Must run with root permissions.
    Use --sudo or run command printed by --print-command.
    Routes are loaded from node/routing.yaml"""
    if not cwd:
        cwd = cuckoocwd.DEFAULT

    if not cuckoocwd.exists(cwd):
        exit_error(
            f"Cuckoo CWD {cwd} does not yet exist. Run "
            f"'cuckoonode createcwd' if this is the first time you are "
            f"running Cuckoo with this CWD path"
        )

    if print_command:
        args = _make_rooter_command(
            cwd, debug, socket, group, iptables, ip, openvpn
        )
        print(" ".join(args))
        return

    if not sudo:
        cuckoocwd.set(cwd)
        if debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO

        try:
            _start_rooter(
                iptables_path=iptables, ip_path=ip, socket_path=socket,
                openvpn_path=openvpn, loglevel=loglevel, socket_group=group
            )
        except (RooterError, StartupError) as e:
            exit_error(f"Error starting rooter: {e}")
        finally:
            call_registered_shutdowns()
    else:
        from subprocess import run
        args = _make_rooter_command(
            cwd, debug, socket, group, iptables, ip, openvpn
        )
        args.insert(0, sudo_path)
        try:
            run(args, shell=False)
        except OSError as e:
            exit_error(f"Failed to start rooter with sudo: {e}")
        finally:
            call_registered_shutdowns()
