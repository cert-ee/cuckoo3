# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import subprocess
from threading import Lock

from .log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

class NetworkCaptureError(Exception):
    pass

class TCPDump:

    DEFAULT_PATH = "/usr/sbin/tcpdump"

    def __init__(self, pcap_path, capture_interface, binary_path=None):
        self.pcap_path = pcap_path
        self.capture_interface = capture_interface
        self.binary_path = binary_path or self.DEFAULT_PATH

        if not os.path.exists(self.binary_path):
            raise NetworkCaptureError(
                f"Tcpdump path {self.binary_path} does not exist."
            )

        self.args = []

        self.ignore_host_port = []
        self.capture_hosts = set()
        self._proc = None

        # Lock is used in stop calls to wrap the changing of 'stopped'
        self.stoplock = Lock()
        self.stopped = False

    @property
    def proc(self):
        if not self._proc:
            raise NetworkCaptureError(
                "No process was started. Cannot read the process handle."
            )

        return self._proc

    def capture_host(self, host_ip):
        self.capture_hosts.add(host_ip)

    def ignore_ip_port(self, ip, port=None):
        self.ignore_host_port.append((ip, port))

    def _create_args(self):
        tcpdump_args = []
        def add_args(*args):
            tcpdump_args.extend(list(args))

        add_args(self.binary_path, "-i", self.capture_interface)
        add_args("-U", "-s", "0", "-n")
        add_args("-w", self.pcap_path)

        prev = None
        for host in self.capture_hosts:
            if not prev:
                add_args("host", host)
            else:
                add_args("and", "host", host)
            prev = True

        for host, port in self.ignore_host_port:
            for direction in ("dst", "src"):
                if not prev:
                    add_args("not")
                else:
                    add_args("and", "not")
                    prev = True

                ignore = [direction, "host", host]
                if port:
                    ignore.extend(["and", direction, "port", str(port)])
                add_args(
                    "(", *ignore, ")"
                )

        return tcpdump_args

    def _find_error(self, err):
        ignore_err_starts = (b"tcpdump: listening on ",)
        ignore_err_ends = (
            b"packet captured", b"packets captured",
            b"packet received by filter", b"packets received by filter",
            b"packet dropped by kernel", b"packets dropped by kernel",
            b"packet dropped by interface", b"packets dropped by interface",
            b"dropped privs to root",
        )

        for line in err.split(b"\n"):
            if not line or line.startswith(ignore_err_starts):
                continue

            if line.endswith(ignore_err_ends):
                continue

            return line

    def start(self):
        args = self._create_args()

        log.debug("Starting tcpdump", args=args)
        try:
            self._proc = subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                close_fds=True
            )
        except OSError as e:
            raise NetworkCaptureError(f"Failed to start tcpdump process. {e}")

        returncode = self._proc.poll()
        if returncode:
            _, err = self._proc.communicate()
            raise NetworkCaptureError(
                f"The tcpdump process exited with code '{returncode}' "
                f"immediately after startup. Stderr: '{err}'"
                ""
                "Did you enable the extra capabilities to allow running "
                "tcpdump as a non-root user and disable AppArmor for tcpdump? "
                "(Only applies to Ubuntu distributions)"
            )

    def force_stop(self):
        if not self._proc:
            return

        if self._proc.poll():
            return

        try:
            self._proc.kill()
        except OSError as e:
            raise NetworkCaptureError(
                f"Failed to stop tcpdump process ({self._proc.pid}). "
                f"Error: {e}"
            )

    def stop(self):
        if not self._proc:
            return

        # Acquire lock before starting stop routine to ensure the stop will
        # only be performed once.
        with self.stoplock:
            if self.stopped:
                return

            self.stopped = True

        returncode = self._proc.poll()
        if returncode:
            _, err = self._proc.communicate()
            raise NetworkCaptureError(
                f"The tcpdump process exited with code '{returncode}' before "
                "it was stopped. This indicates some error occurred. "
                f"Stderr: '{err}'"
                ""
                "Did you enable the extra capabilities to allow running "
                "tcpdump as a non-root user and disable AppArmor for tcpdump? "
                "(Only applies to Ubuntu distributions)"
            )

        log.debug("Stopping tcpdump process", pid=self._proc.pid)
        try:
            self._proc.terminate()
        except Exception as e:
            log.warning(
                "Error sending sigterm to process. Sending sigkill.",
                error=e, pid=self._proc.pid
            )
            self.force_stop()

        timeout = 60
        if not self._proc.poll():
            log.debug(
                "Reading tcpdump process stderr. Process has not exited yet. "
                "Waiting for it to exit.", pid=self._proc.pid, timeout=60
            )

        read_stderr = False
        try:
            err = self._find_error(self._proc.communicate(timeout=timeout)[1])
            read_stderr = True
        except subprocess.TimeoutExpired:
            log.error(
                "Timeout expired waiting for tcpdump process to stop. "
                "Sending sigkill", pid=self._proc.pid
            )
            self.force_stop()
        except ValueError as e:
            log.error("Failure reading output from stderr", error=e)

        if not read_stderr:
            try:
                err = self._find_error(self._proc.communicate(timeout=10)[1])
            except subprocess.TimeoutExpired:
                raise NetworkCaptureError(
                    f"Tcpdump has not exited after sigkill. Stopping waiting. "
                    f"PID {self._proc.pid}.",
                )

        if err:
            raise NetworkCaptureError(f"tcpdump encountered an error: {err}")
