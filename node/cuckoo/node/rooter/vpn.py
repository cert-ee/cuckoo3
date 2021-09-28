# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import random
import subprocess
import time
from pathlib import Path
from tempfile import gettempdir
from threading import RLock
from uuid import uuid4

from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.storage import delete_file

from .errors import (
    RooterError, AutoVPNError, MaxConnectionsError, RouteUnavailableError
)

log = CuckooGlobalLogger("rooter.vpn")


class OpenVPN:
    """Wrapper around the openvpn binary path."""

    def __init__(self, openvpn_path):
        self.path = openvpn_path

    def start_vpn(self, client_config_path, route_up_script_path, devname,
                  dropuser="", dropgroup="", envs={}, cwd=None,
                  stdout=None, stderr=None, iproute_path=None):
        command = [
            self.path,
            "--config", str(client_config_path),
            "--script-security", "2",
            "--route-up", str(route_up_script_path),
            "--dev", devname, "--route-noexec",
            "--dev-type", "tun",
            # Set --up/down so up/down commands in ovpn/config files
            # are overridden. Most of these scripts by providers perform
            # unwanted actions etc. If we do need this, add support for these
            # later.
            "--up", "/bin/true",
            "--down", "/bin/true"
        ]

        if dropuser:
            command.extend(["--user", dropuser])

        if dropgroup:
            command.extend(["--group", dropgroup])

        if iproute_path:
            command.extend(["--iproute", str(iproute_path)])

        for k, v in envs.items():
            command.extend(["--setenv", str(k), str(v)])

        log.debug("Running OpenVPN starting command", command=command)
        try:
            return subprocess.Popen(
                command, stdout=stdout, stderr=stderr, shell=False,
                close_fds=True, cwd=cwd
            )
        except OSError as e:
            raise AutoVPNError(
                f"Failed to start OpenVPN process with command: {command}. {e}"
            )

class VPNProvider:
    """A tracker of for a 'vpn provider' or group of VPNs with a shared
    limit of devices/connections. Used to automatically start a VPN for
    a specific country or return one that is already running."""

    def __init__(self, rooterctx, name, max_connections):
        self.ctx = rooterctx
        self.name = name
        self.max_connections = max_connections
        self.available_vpns = {}
        self._enabled_vpns = []

        self.enabled_vpns_lock = RLock()

    @property
    def countries(self):
        return list(self.available_vpns.keys())

    def add_available_vpn(self, country, vpntype, config_path, up_script):
        if vpntype != "openvpn":
            raise AutoVPNError(f"Unsupported VPN type: {vpntype}")

        self.available_vpns.setdefault(country.lower(), []).append({
            "type": vpntype,
            "config_path": Path(config_path),
            "up_script": Path(up_script)
        })

    def release_vpn(self, vpn):
        """Remove the given vpn from enabled vpns. Should be called after
        stopping a vpn or no longer needing it."""
        with self.enabled_vpns_lock:
            if not vpn.stopped:
                try:
                    vpn.stop()
                except AutoVPNError as e:
                    raise RooterError(
                        f"Failed to stop VPN {vpn.name}. Cannot remove "
                        f"from enabled connections without it being "
                        f"stopped. {e}"
                    )

            if vpn in self._enabled_vpns:
                self._enabled_vpns.remove(vpn)

    def _stop_unused(self):
        with self.enabled_vpns_lock:
            log.debug("Looking for unused VPNs to stop")
            for vpn in self._enabled_vpns[:]:
                if vpn.in_use:
                    log.debug(
                        "VPN still in use", vpn=vpn.name, users=vpn.user_count
                    )
                    continue

                log.info("Stopping unused vpn", vpn=vpn.name)
                self.release_vpn(vpn)
                return True

        return False

    def _start_vpn(self, info, country):
        country = country.lower()
        with self.enabled_vpns_lock:
            if len(self._enabled_vpns) >= self.max_connections:
                log.debug(
                    "Cannot start new VPN for country. maximum amount of "
                    "connections reached", provider=self.name, country=country
                )
                if not self._stop_unused():
                    raise MaxConnectionsError(
                        f"Cannot start VPN for country {country}, "
                        f"maximum connections of {self.max_connections} "
                        f"reached. "
                    )

            conf_path = info["config_path"]
            name = f"{self.name}-{conf_path.name}"
            logname = f"{name}.log"
            vpn = OpenVPNAutoVPN(
                self.ctx, provider=self,
                routing_table=self.ctx.routing_tables.get_next_table(),
                interface=self.ctx.interfaces.new_interface(postfix="vpn"),
                country=country, name=name,
                config_path=conf_path,
                up_script=info["up_script"],
                log_path=self.ctx.logpath.joinpath(logname)
            )

            try:
                vpn.start()
            except AutoVPNError as e:
                raise AutoVPNError(
                    f"Failed to start VPN {conf_path} "
                    f"of provider {self.name}. {e}"
                )
            except TimeoutError as e:
                # Stop VPN process if it was not online within timeout.
                try:
                    vpn.stop()
                finally:
                    raise AutoVPNError(
                        f"VPN {conf_path} of provider {self.name} was not "
                        f"online within timeout. {e}"
                    )

            self._enabled_vpns.append(vpn)
            vpn.increment_users()
            return vpn

    def _random_available(self, country=None):
        if not country:
            # Get a random available country if none is specified.
            country = random.choice(list(self.available_vpns.keys()))

        # Choose a random vpn from the country
        return random.choice(self.available_vpns[country]), country

    def get_vpn(self, country=None):
        if country:
            return self._get_vpn_country(country)

        with self.enabled_vpns_lock:
            if self._enabled_vpns:
                vpn = self._enabled_vpns[0]
                vpn.increment_users()
                return vpn

            # Choose a random available vpn
            info, country = self._random_available()
            return self._start_vpn(info, country)

    def _get_vpn_country(self, country):
        country = country.lower()
        if country not in self.available_vpns:
            return None

        with self.enabled_vpns_lock:
            for vpn in self._enabled_vpns:
                if vpn.country != country:
                    continue

                vpn.increment_users()
                return vpn

            info, _ = self._random_available(country)
            return self._start_vpn(info, country)

    def stop_all(self):
        with self.enabled_vpns_lock:
            for vpn in self._enabled_vpns[:]:
                try:
                    vpn.stop()
                except RooterError as e:
                    log.exception("Error stopping VPN", vpn=vpn.name, error=e)

class VPN:
    """Wrapper around an preconfigured VPN."""

    def __init__(self, rooterctx, routing_table, interface, country, name):
        self.ctx = rooterctx
        self.routing_table = routing_table
        self.interface = interface
        self.country = country
        self._name = name

    @property
    def name(self):
        return self._name

    def increment_users(self):
        pass

    def decrement_users(self):
        pass


def _unique_filepath_string():
    return Path(gettempdir(), f"rooter-{uuid4()}")

class OpenVPNAutoVPN(VPN):
    """Wrapper around an OpenVPN configuration file path. Should be part
    of a VPNProvider class instance. The VPNProvider class uses these to
    start/stop specific VPNs."""

    def __init__(self, rooterctx, provider, routing_table, interface, name,
                 country, config_path, up_script, log_path, up_timeout=60):
        super().__init__(rooterctx, routing_table, interface, country, name)
        self._provider = provider
        self.config_path = config_path
        self.up_script = up_script
        self._up_timeout = up_timeout

        self._start_lock = RLock()
        self._openvpn_proc = None
        self._logpath = log_path
        self._logfile = None
        self._user_count = 0

    @property
    def stopped(self):
        return self._openvpn_proc is None \
               or self._openvpn_proc.poll() is not None

    @property
    def user_count(self):
        """Approximate count of current VPN user."""
        return self._user_count

    @property
    def in_use(self):
        return self._user_count > 0

    def increment_users(self):
        with self._provider.enabled_vpns_lock:
            self._user_count += 1

    def decrement_users(self):
        with self._provider.enabled_vpns_lock:
            self._user_count -= 1

    def _check_up(self):
        if self._openvpn_proc.poll() is not None:
            raise AutoVPNError(
                f"OpenVPN process has exited with code:"
                f" {self._openvpn_proc.returncode}. See log for errors."
            )

        if not self.interface.is_up():
            raise AutoVPNError(
                f"OpenVPN started, but interface "
                f"{self.interface.name} is not up"
            )

    def stop(self):
        with self._start_lock:
            if not self._openvpn_proc or self.stopped:
                return

            log.info("Stopping VPN", country=self.country, name=self.name)
            try:
                self._openvpn_proc.terminate()
            except OSError as e:
                raise AutoVPNError(
                    f"Error while sending SIGTERM to OpenVPN process "
                    f"({self._openvpn_proc.pid}) for : "
                    f"{self.interface.name}, {self.config_path}. {e}"
                )

            waited = 0
            timeout = False
            while self._openvpn_proc.poll() is None:
                if waited >= 10:
                    timeout = True
                    break
                time.sleep(1)
                waited += 1

            if timeout:
                try:
                    self._openvpn_proc.kill()
                    # Clear openvpn process object to ensure it seen
                    # as stopped. We will not be waiting for the
                    # process to stop after the SIGKILL.
                    self._openvpn_proc = None
                except OSError as e:
                    raise AutoVPNError(
                        f"Error while sending SIGKILL to OpenVPN process "
                        f"({self._openvpn_proc.pid}) for : "
                        f"{self.interface.name}, {self.config_path}. {e}"
                    )

            self.routing_table.release()
            self.interface.release()

            self._provider.release_vpn(self)

    def start(self):
        with self._start_lock:
            if self._openvpn_proc and self._openvpn_proc.poll() is None:
                return

            log.info(
                "Starting VPN", country=self.country, name=self.name,
                vpnlog=self._logpath
            )
            self._logfile = open(self._logpath, "ab")

            unique_path = _unique_filepath_string()
            self._openvpn_proc = self.ctx.openvpn.start_vpn(
                # Set the openvpn process to the path of the config. Many
                # configs contain imports that assume the cwd is the directory
                # of the config.
                cwd=self.config_path.parent,
                client_config_path=self.config_path,
                route_up_script_path=self.up_script,
                devname=self.interface.name, stderr=self._logfile,
                iproute_path=self.ctx.ip.path,
                stdout=self._logfile,  envs={
                    "CUCKOO_IP_PATH": self.ctx.ip.path,
                    "CUCKOO_ROUTING_TABLE": self.routing_table.id,
                    "CUCKOO_READY_FILE": unique_path
                }
            )

            waited = 0
            while not unique_path.is_file():
                if self._openvpn_proc.poll() is not None:
                    raise AutoVPNError(
                        f"VPN exited during startup. "
                        f"Exit code: {self._openvpn_proc.returncode}. "
                        f"See logs {self._logpath}."
                    )

                if waited >= self._up_timeout:
                    raise TimeoutError(
                        f"VPN not up within timeout. "
                        f"Ready file ({unique_path}) not created."
                    )
                time.sleep(1)
                waited += 1

            delete_file(unique_path)

            self._check_up()


class VPNs:
    """A tracker that wraps around all types of VPNs
    (preconfigured and VPNProviders that makes the asking for a VPN
    more abstract."""

    def __init__(self):
        self._providers = []
        self._preconfigured = []

    @property
    def vpns_available(self):
        return len(self._providers) + len(self._preconfigured) > 0

    @property
    def countries(self):
        coutries = []
        for vpn in self._preconfigured:
            coutries.append(vpn.country)

        for provider in self._providers:
            coutries.extend(provider.countries)

        return list(set(coutries))

    def add_preconfigured_vpn(self, rooterctx, routing_table_id,
                              interface_name, country, name):
        self._preconfigured.append(VPN(
            rooterctx=rooterctx,
            routing_table=rooterctx.routing_tables.get_existing_table(
                routing_table_id
            ),
            interface=rooterctx.interfaces.get_existing_interface(
                interface_name
            ), country=country, name=name
        ))

    def add_provider(self, provider):
        self._providers.append(provider)

    def get_vpn(self, country=None):
        for vpn in self._preconfigured:
            if country:
                if vpn.country == country:
                    return vpn
            else:
                return vpn

        vpn = None
        max_conns_reached = False
        for provider in self._providers:
            try:
                log.debug(
                    "Asking provider for vpn",
                    provider=provider.name, country=country
                )
                vpn = provider.get_vpn(country)
                if vpn:
                    break
            except MaxConnectionsError as e:
                log.debug(
                    "Provider reached maximum connections",
                    provider=provider.name, error=e
                )
                max_conns_reached = True
                continue

        if vpn:
            return vpn

        if max_conns_reached:
            raise RouteUnavailableError(
                f"All VPN providers have reached the maximum amount of "
                f"connections. Cannot create new VPN for '{country}'"
            )

        raise RouteUnavailableError(
            f"No VPN available"
            f"{'' if not country else f' for country {country}'}"
        )

    def stop_all(self):
        for provider in self._providers:
            log.debug("Stopping all VPNs for provider", provider=provider.name)
            provider.stop_all()
