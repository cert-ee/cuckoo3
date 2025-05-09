# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import errno
import json
import os.path
import socket
import time
from datetime import datetime
from distutils.version import LooseVersion
from pathlib import Path, PureWindowsPath
from tempfile import mkdtemp
from zipfile import ZipFile, ZipInfo

import requests

from .storage import Paths, AnalysisPaths, TaskPaths
from .importing import zinfo_has_illegal_chars, should_ignore_zinfo


class AgentError(Exception):
    pass


class WaitTimeout(AgentError):
    pass


class AgentConnectionError(AgentError):
    pass


class UnsupportedMethod(AgentError):
    pass


class OutdatedAgentError(AgentError):
    pass


class StagerError(Exception):
    pass


class PayloadExecFailed(StagerError):
    pass


class Agent:
    def __init__(self, ip, port=8000):
        self.ip = ip
        self.port = port

    def _make_url(self, path):
        if not path.startswith("/"):
            raise ValueError("Path must start with /")

        return f"http://{self.ip}:{self.port}{path}"

    def _status_code_err(self, response):
        code = response.status_code

        try:
            json_resp = response.json()
        except ValueError:
            json_resp = {}

        if code == 400:
            return AgentError(
                f"Incorrect agent usage for {response.url}: {json_resp.get('message')}"
            )
        if code == 404:
            return UnsupportedMethod(f"Unsupported method: {response.url}")
        if code == 500:
            return AgentError(
                f"Fatal agent error when requesting: {response.url}. "
                f"Error: {json_resp.get('message')}. "
                f"Traceback: {json_resp.get('traceback')}"
            )

        return AgentError(
            f"HTTP status {response.status_code} from agent when "
            f"requesting: {response.url}."
            f" Error {json_resp.get('message', '')}"
        )

    def _make_session(self):
        ses = requests.Session()
        ses.trust_env = False
        ses.proxies = None
        return ses

    def _get_json(self, response):
        try:
            return response.json()
        except ValueError:
            raise AgentError(
                f"Expected JSON response for url: {response.url}. "
                f"Got {response.content[:24]}"
                f"{'...' if len(response.content) > 24 else ''}"
            )

    def _get(self, method, **kwargs):
        ses = self._make_session()
        url = self._make_url(method)
        try:
            response = ses.get(url, **kwargs)
        except (requests.ConnectionError, requests.exceptions.Timeout) as e:
            raise AgentConnectionError(f"Failed performing HTTP GET on: {url}: {e}")

        if response.status_code != 200:
            raise self._status_code_err(response)

        return response

    def _post(self, method, **kwargs):
        ses = self._make_session()
        url = self._make_url(method)
        try:
            response = ses.post(url, **kwargs)
        except (requests.ConnectionError, requests.exceptions.Timeout) as e:
            raise AgentConnectionError(f"Failed performing HTTP POST on: {url}: {e}")

        if response.status_code != 200:
            raise self._status_code_err(response)

        return response

    def wait_online(self, timeout=120):
        waited = 0
        while waited < timeout:
            start = time.monotonic()
            if waited:
                # Wait a while to let the host become reachable or to let the
                # agent start up. Wait after the first check only, as to not
                # wait and then exit the loop.
                time.sleep(1)

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.settimeout(min(timeout, 3))
                s.connect((self.ip, self.port))
                return
            except socket.timeout:
                pass

            except OSError as e:
                ignore = (errno.EHOSTUNREACH, errno.ECONNREFUSED, errno.ECONNABORTED)
                if e.errno not in ignore:
                    raise

            finally:
                try:
                    s.close()
                except socket.error:
                    pass

            waited += int(time.monotonic() - start)

        raise WaitTimeout(
            f"Could not connect to: {self.ip}:{self.port} within timeout of "
            f"{timeout} seconds."
        )

    def version(self):
        response = self._get_json(self._get("/"))
        return response["version"]

    def version_check(self):
        version = LooseVersion(self.version())
        if version < LooseVersion("0.9"):
            raise OutdatedAgentError(
                f"The minimum required Cuckoo agent version is 0.9. "
                f"Agent: {self.ip}:{self.port} is version: {version}"
            )

        return version

    def mkdtemp(self):
        response = self._get_json(self._get("/mkdtemp"))
        return response["dirpath"]

    def extract_zip(self, zip_fp, extract_dir):
        self._post("/extract", files={"zipfile": zip_fp}, data={"dirpath": extract_dir})

    def execute(self, command, cwd, timeout=None):
        response = self._get_json(
            self._post(
                "/execute", data={"command": command, "cwd": cwd}, timeout=timeout
            )
        )
        return response.get("stdout", ""), response.get("stderr", "")

    def pin_host_ip(self):
        """Causes the ip of the client sending the request to be the only one
        allowed to make requests to the agent. Others will be denied."""
        self._get("/pinning")

    def agent_path(self):
        """Get the filepath of the agent on the guest."""
        response = self._get_json(self._get("/path"))
        return response["filepath"]

    def delete_agent(self):
        """Delete the agent file on the guest"""
        agent_path = self.agent_path()
        self._post("/remove", data={"path": agent_path})

    def delete_file(self, path):
        self._post("/remove", data={"path": path})

    def kill_agent(self):
        """Stop the agent process on the guest"""
        self._get("/kill")


class Payload:
    """Create a payload zip in the system tmp directory. Use add_file and
    add_str to populate the zip and call"""

    def __init__(self):
        self._tmpdir = Path(mkdtemp())
        self._path = Path(self._tmpdir).joinpath("payload.zip")
        self._zip = None
        self._zip_fp = None

    @property
    def fp(self):
        """Retrieve a binary read mode fp for the created payload zip.
        It is no longer possible to add to the payload after retrieving
        this."""
        if self._zip_fp:
            return self._zip_fp

        if not self._path.is_file():
            raise FileNotFoundError(
                "No payload created yet. Cannot return a file pointer to it."
            )

        if self._zip.fp:
            self.close_zip()

        self._zip_fp = open(self._path, "rb")
        return self._zip_fp

    def open_zip(self):
        self._zip = ZipFile(self._path, mode="w")

    def close_zip(self):
        self._zip.fp.flush()
        self._zip.close()

    def __enter__(self):
        if not self._zip:
            self.open_zip()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_zip()

    def add_file(self, path, archive_path=""):
        """Add the existing file from given path to the root of the payload
        zip or at the given archive_path."""
        if not self._zip:
            self.open_zip()

        if not self._zip.fp:
            raise ValueError(
                "It is not possible to write to the payload retrieving its fp."
            )

        self._zip.write(path, arcname=archive_path or path.name)

    def add_str(self, strdata, archive_path):
        """Add the given strdata as the file specified in archive_path."""
        if not self._zip:
            self.open_zip()

        if not self._zip.fp:
            raise ValueError(
                "It is not possible to write to the payload retrieving its fp."
            )

        self._zip.writestr(ZipInfo(archive_path), strdata)

    def add_dir(self, dirpath, archive_path=""):
        for curpath, dirs, files in os.walk(dirpath, followlinks=False):
            for file in files:
                filepath = Path(curpath, file)
                relpath = os.path.relpath(filepath, dirpath)
                if archive_path:
                    relpath = Path(archive_path, relpath)

                self.add_file(filepath, archive_path=relpath)

    def cleanup(self):
        """Delete the created payload file and closes all open fds."""
        if self._zip:
            self._zip.close()

        if self._zip_fp:
            self._zip_fp.close()

        if self._path.exists():
            self._path.unlink()

        if self._tmpdir.exists():
            self._tmpdir.rmdir()


def get_default_version(path):
    if not path.is_file():
        raise StagerError(f"Default version file does not exist: {path}")

    version = path.read_text().strip()
    if not version:
        raise StagerError(f"Default version file is empty: {path}")

    return version


class StagerHelper:
    name = ""
    platforms = []

    STAGER_BINARY = ""
    MONITOR_BINARY = ""

    MONITOR_NAME = ""

    DEFAULT_MONITOR = "default_monitor"
    DEFAULT_STAGER = "default_stager"

    def __init__(self, agent, task, analysis, resultserver, logger):
        self.agent = agent
        self.task = task
        self.analysis = analysis
        self.resultserver = resultserver

        self.log = logger

        # Should be set after calling prepare with a ready Payload instance.
        self.payload = None

    @classmethod
    def find_stager_dir(cls, platform, archirecture, version=""):
        base = Paths.monitor(platform, archirecture, cls.MONITOR_NAME)
        # Find 'default' version string from default_stager file.
        if not version:
            version = get_default_version(base.joinpath(cls.DEFAULT_STAGER))

        stager_path = base.joinpath("stager", version)
        if not stager_path.is_dir():
            raise StagerError(f"Stager {stager_path} does not exist.")

        stager_binary = stager_path.joinpath(cls.STAGER_BINARY)
        if not stager_binary.is_file():
            raise StagerError(f"Stager binary {stager_binary} does not exist.")

        return stager_path

    @classmethod
    def find_monitor_dir(cls, platform, archirecture, version=""):
        base = Paths.monitor(platform, archirecture, cls.MONITOR_NAME)
        # Find 'default' version string from default_monitor file.
        if not version:
            version = get_default_version(base.joinpath(cls.DEFAULT_MONITOR))

        monitor_path = base.joinpath("monitor", version)
        if not monitor_path.is_dir():
            raise StagerError(f"Monitor {monitor_path} does not exist.")

        monitor_binary = monitor_path.joinpath(cls.MONITOR_BINARY)
        if not monitor_binary.is_file():
            raise StagerError(f"Monitor binary {monitor_binary} does not exist.")

        return monitor_path

    def get_command_args(self):
        if self.task.command:
            return self.task.command

        if self.analysis.settings.command:
            return self.analysis.settings.command

        return []

    def dump_payload_log(self, logstr):
        with open(TaskPaths.payloadlog(self.task.id), "w") as fp:
            fp.write(logstr)

    def prepare(self):
        raise NotImplementedError

    def deliver_payload(self):
        raise NotImplementedError

    def cleanup(self):
        if self.payload:
            self.payload.cleanup()


class TmStage(StagerHelper):
    name = "tmstage"
    platforms = ["windows"]

    MONITOR_NAME = "threemon"

    STAGER_BINARY = "tmstage.exe"
    MONITOR_BINARY = "threemon.sys"

    def _build_settings(self, debug, resultserver, options, target, is_archive):
        return json.dumps(
            {
                "debug": debug,
                "host": f"{resultserver.listen_ip}:{resultserver.listen_port}",
                "launch": self.get_command_args(),
                "clock": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "options": options,
                "target": target,
                "archive": is_archive,
            }
        )

    def prepare(self):
        is_archive = False
        # If the target is a file and has an extraction path, set the target
        # to the last filename of the extraction path.
        if self.analysis.category == "file" and self.analysis.target.extrpath:
            is_archive = True
            target = self.analysis.target.extrpath[-1]
        # The target is a file or url. The target attribute gives either a
        # file name or a url, depending on the container type.
        else:
            target = self.analysis.target.target

        options = self.analysis.settings.options
        settings = self._build_settings(
            debug=False,
            resultserver=self.resultserver,
            options=options,
            target=target,
            is_archive=is_archive,
        )

        stager_filepath = self.find_stager_dir(
            platform="windows",
            archirecture="amd64",
            version=options.get("stager.version"),
        )
        monitor_filepath = self.find_monitor_dir(
            platform="windows",
            archirecture="amd64",
            version=options.get("monitor.version"),
        )

        with Payload() as pay:
            pay.add_str(settings, "settings.json")

            # Monitor path contains threemon and other tls monitor dll
            pay.add_dir(monitor_filepath)
            # Stager path contains stager binary and other things such as
            # auxiliary modules.
            pay.add_dir(stager_filepath)

            if self.analysis.category == "file":
                if is_archive:
                    pay.add_file(
                        AnalysisPaths.zipified_file(self.analysis.id), "payload.dat"
                    )
                else:
                    pay.add_file(
                        AnalysisPaths.submitted_file(self.analysis.id), "payload.dat"
                    )

            self.payload = pay

    def deliver_payload(self):
        if not self.payload:
            raise ValueError("No payload set to deliver")

        try:
            agent_version = self.agent.version_check()
        except AgentError as e:
            raise StagerError(f"Outdated agent. {e}")

        # Delete the agent Python file. It can remain running without the file
        try:
            # Only try to delete agent if it is 1.0, this agent is still a
            # python file and can be deleted. The new agent is an exe.
            if agent_version < LooseVersion("1.0"):
                self.agent.delete_agent()
        except AgentError as e:
            # A failing deletion is not fatal, we can still continue. It can
            # indicate permission problems, however. So we do log it.
            self.log.warning("Failed to delete agent file", error=e)
        try:
            tmpdir = self.agent.mkdtemp()
        except AgentError as e:
            raise StagerError(f"Failed to create tmp dir: {e}")

        try:
            self.agent.extract_zip(self.payload.fp, tmpdir)
        except AgentError as e:
            raise StagerError(f"Failed to extract payload: {e}")

        stager_path = PureWindowsPath(tmpdir, self.STAGER_BINARY)
        try:
            # A timeout is important when delivering the payload in case the
            # agent stops responding.
            stdout, stderr = self.agent.execute(
                stager_path,
                cwd=tmpdir,
                timeout=60,  # TODO use task timeout?
            )
        except AgentError as e:
            raise StagerError(f"Failed to execute stager: {e}")

        self.dump_payload_log(stderr)

        for line in stderr.split("\n"):
            for m in ("Failed to", "Payload error", "Exception"):
                if m in line:
                    if "image=" not in line and "command=" not in line:
                        raise PayloadExecFailed(
                            f"Payload execution failed: {line}. {stderr}"
                        )

        # Delete the stager executable.
        try:
            self.agent.delete_file(stager_path)
        except AgentError as e:
            self.log.warning("Failed to delete stager executable", error=e)

        # Kill the agent. We no longer are using the analyzer, making it
        # useless to leave it running. It only increases the chance of it
        # being used as a means of anti-analysis.
        try:
            self.agent.kill_agent()
        except AgentError as e:
            # A failing kill is not fatal, we can still continue. It can
            # indicate permission problems, however. So we do log it.
            self.log.warning("Failed to kill agent.", error=e)


_stagers = {"threemon": TmStage}

DEFAULT_MONITOR_FILE = "default"


def find_stager(platform, arch="amd64"):
    arch = arch.lower()
    monitor_path = Paths.monitor(platform, arch)
    if not monitor_path.is_dir():
        raise StagerError(
            f"No monitor exists for platform '{platform}' with architecture: '{arch}'"
        )

    monitor_name = get_default_version(
        monitor_path.joinpath(DEFAULT_MONITOR_FILE)
    ).lower()

    if not monitor_path.joinpath(monitor_name).is_dir():
        raise StagerError(f"No monitor path for default monitor {monitor_name} exists.")

    stager = _stagers.get(monitor_name)
    if not stager:
        raise StagerError(f"No stager helper is mapped for monitor name {stager}")

    return stager


def unpack_monitor_components(zip_path, unpackto):
    if not Path(unpackto).is_dir():
        raise NotADirectoryError(f"Not a valid dir to unpack to: {unpackto}")

    monitorpath = Path(unpackto)
    with ZipFile(zip_path, "r") as zfile:
        files = zfile.infolist()
        for entry in files:
            if zinfo_has_illegal_chars(entry) or should_ignore_zinfo(entry):
                raise ValueError(
                    "Archive entry contains illegal characters or is of a "
                    f"forbidden type (symlinks). Do not unpack. Entry: {entry}"
                )

            print(
                f"Unpacking {entry.filename} -> {monitorpath.joinpath(entry.filename)}"
            )
            zfile.extract(entry, monitorpath)
