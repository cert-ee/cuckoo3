# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import errno
import json
import socket
import time
from datetime import datetime
from distutils.version import StrictVersion
from pathlib import Path, PureWindowsPath
from tempfile import mkdtemp
from zipfile import ZipFile, ZipInfo

import requests

from .storage import Paths, AnalysisPaths, TaskPaths

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
                f"Incorrect agent usage for {response.url}:"
                f" {json_resp.get('message')}"
            )
        if code == 404:
            return UnsupportedMethod(
                f"Unsupported method: {response.url}"
            )
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
        except requests.ConnectionError as e:
            raise AgentConnectionError(
                f"Failed performing HTTP GET on: {url}: {e}"
            )

        if response.status_code != 200:
            raise self._status_code_err(response)

        return response

    def _post(self, method, **kwargs):
        ses = self._make_session()
        url = self._make_url(method)
        try:
            response = ses.post(url, **kwargs)
        except requests.ConnectionError as e:
            raise AgentConnectionError(
                f"Failed performing HTTP POST on: {url}: {e}"
            )

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
                ignore = (errno.EHOSTUNREACH, errno.ECONNREFUSED,
                          errno.ECONNABORTED)
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
        version = self.version()
        if StrictVersion(version) < StrictVersion("0.9"):
            raise OutdatedAgentError(
                f"The minimum required Cuckoo agent version is 0.9. "
                f"Agent: {self.ip}:{self.port} is version: {version}"
            )

    def mkdtemp(self):
        response = self._get_json(self._get("/mkdtemp"))
        return response["dirpath"]

    def extract_zip(self, zip_fp, extract_dir):
        self._post(
            "/extract", files={"zipfile": zip_fp},
            data={"dirpath": extract_dir}
        )

    def execute(self, command, cwd):
        response = self._get_json(self._post(
            "/execute", data={"command": command, "cwd": cwd}
        ))
        return response["stdout"], response["stderr"]

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

        if not archive_path:
            archive_path = Path(path).name

        self._zip.write(path, arcname=archive_path)

    def add_str(self, strdata, archive_path):
        """Add the given strdata as the file specified in archive_path."""
        if not self._zip:
            self.open_zip()

        if not self._zip.fp:
            raise ValueError(
                "It is not possible to write to the payload retrieving its fp."
            )

        self._zip.writestr(ZipInfo(archive_path), strdata)

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

class StagerHelper:

    name = ""
    platforms = []
    archs = []

    STAGER_BINARY = ""
    MONITOR_BINARY = ""

    def __init__(self, agent, task, analysis, identification, result_ip,
                 result_port):
        self.agent = agent
        self.task = task
        self.analysis = analysis
        self.identification = identification
        self.result_ip = result_ip
        self.result_port = result_port

        # Should be set after calling prepare with a ready Payload instance.
        self.payload = None

    @staticmethod
    def get_latest_version(path):
        if not path.is_file():
            raise StagerError(f"Latest version file does not exist: {path}")

        version = path.read_text().strip()
        if not version:
            raise StagerError(f"Latest version file is empty: {path}")

        return version

    def find_stager_binary(cls, platform, archirecture, version=""):
        base = Path(Paths.monitor(platform, archirecture))
        # Find 'latest' version hash from latest_stager file.
        if not version:
            version = cls.get_latest_version(base.joinpath("latest_stager"))

        stager_path = base.joinpath("stager", version, cls.STAGER_BINARY)
        if not stager_path.is_file():
            raise StagerError(f"Stager {stager_path} does not exist.")

        return stager_path

    def find_monitor_binary(cls, platform, archirecture, version=""):
        base = Path(Paths.monitor(platform, archirecture))
        # Find 'latest' version hash from latest_monitor file.
        if not version:
            version = cls.get_latest_version(base.joinpath("latest_monitor"))

        monitor_path = base.joinpath("monitor", version, cls.MONITOR_BINARY)
        if not monitor_path.is_file():
            raise StagerError(f"Monitor {monitor_path} does not exist.")

        return monitor_path

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
    archs = ["amd64"]

    STAGER_BINARY = "tmstage.exe"
    MONITOR_BINARY = "threemon.sys"

    @staticmethod
    def _build_settings(debug, resultserver, options, target, is_archive):
        return json.dumps({
            "debug": debug,
            "host": resultserver,
            "launch": [],
            "clock": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "options": options,
            "target": target,
            "archive": is_archive,
        })

    def prepare(self):
        if self.identification.target.extrpath:
            is_archive = True
            target = self.identification.target.extrpath[-1]
        else:
            is_archive = False
            target = self.identification.target.filename

        options = self.analysis.settings.options
        settings = self._build_settings(
            debug=True, resultserver=f"{self.result_ip}:{self.result_port}",
            options=options, target=target, is_archive=is_archive
        )

        stager_filepath = self.find_stager_binary(
            platform="windows", archirecture="amd64",
            version=options.get("stager.version")
        )
        monitor_filepath = self.find_monitor_binary(
            platform="windows", archirecture="amd64",
            version=options.get("monitor.version")
        )

        with Payload() as pay:
            pay.add_str(settings, "settings.json")
            pay.add_file(stager_filepath, self.STAGER_BINARY)
            pay.add_file(monitor_filepath, self.MONITOR_BINARY)

            if is_archive:
                pay.add_file(
                    AnalysisPaths.zipified_file(self.analysis.id),
                    "payload.dat"
                )
            else:
                pay.add_file(
                    AnalysisPaths.submitted_file(self.analysis.id),
                    "payload.dat"
                )

            self.payload = pay

    def deliver_payload(self):
        if not self.payload:
            raise ValueError(f"No payload set to deliver")

        # Delete the agent Python file. It can remain running without the file
        try:
            self.agent.delete_agent()
        except AgentError as e:
            # A failing deletion is not fatal, we can still continue. It can
            # indicate permission problems, however. So we do log it.
            print(f"Failed to delete agent file: {e}")
        try:
            tmpdir = self.agent.mkdtemp()
        except AgentError as e:
            raise StagerError(f"Failed to create tmp dir: {e}")

        try:
            self.agent.extract_zip(self.payload.fp, tmpdir)
        except AgentError as e:
            raise StagerError(f"Failed to extract payload: {e}")

        command = PureWindowsPath(tmpdir, self.STAGER_BINARY)
        try:
            stdout, stderr = self.agent.execute(command, cwd=tmpdir)
        except AgentError as e:
            raise StagerError(f"Failed to execute stager: {e}")

        self.dump_payload_log(stderr)

        # Very ugly check until we can properly separate info, warn, and fatal
        # log messages. All messages are now in stderr. TODO fix
        for line in stderr.split("\n"):
            if "Failed to" in line:
                if "image=" not in line and "command=" not in line:
                    raise PayloadExecFailed(
                        f"Payload execution failed: {line}. {stderr}"
                    )

        # Kill the agent. We no longer are using the analyzer, making it
        # useless to leave it running. It only increases the chance of it
        # being used as a means of anti-analysis.
        try:
            self.agent.kill_agent()
        except AgentError as e:
            # A failing kill is not fatal, we can still continue. It can
            # indicate permission problems, however. So we do log it.
            print(f"Failed to kill agent: {e}")

_stagers = {
    "windows": TmStage
}

def find_stager(platform, arch="amd64"):
    stager = _stagers.get(platform)
    if not stager:
        return None

    # TODO actually use arch in machine configurations.
    if arch not in stager.archs:
        return None

    return stager

def unpack_monitor_components(zip_path, unpackto):
    # TODO replace with proper monitor/stager etc unpack and updating code
    # TEMP
    if not Path(unpackto).is_dir():
        raise NotADirectoryError(f"Not a valid dir to unpack to: {unpackto}")

    monitorpath = Path(unpackto)

    archs = ["amd64"]
    unpackdirs = ["monitor/windows"]
    unpackdirs.extend(
        [str(Path("monitor/windows").joinpath(arch)) for arch in archs]
    )
    with ZipFile(zip_path, "r") as zfile:
        files = zfile.namelist()
        for entry in files:
            if ".." in entry:
                raise ValueError(
                    f"Path traversal archive in archive: {zip_path}. "
                    f"Do not unpack."
                )

            if not entry.startswith(tuple(unpackdirs)):
                continue

            print(f"Unpacking {entry} -> {monitorpath.joinpath(entry)}")
            zfile.extract(entry, monitorpath)
