# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import json
import os.path
import shlex
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock

from .analyses import (
    Kinds as AnalysisKinds, AnalysisError, Settings, get_state,
    States as AnalysisStates
)
from .clients import StateControllerClient, ActionFailedError
from .log import CuckooGlobalLogger
from .machines import find_in_lists
from .node import NodeInfos, read_nodesinfos_dump
from .storage import File, Binaries, Paths, AnalysisPaths, make_analysis_folder
from .strictcontainer import (
    Analysis, SubmittedFile, SubmittedURL, Platform, Route
)
from .utils import force_valid_encoding, browser_to_tag

log = CuckooGlobalLogger(__name__)

class SubmissionError(Exception):
    pass


def _write_analysis(analysis_id, settings, target_strictcontainer):
    analysis_info = Analysis(**{
        "id": analysis_id,
        "kind": AnalysisKinds.STANDARD,
        "state": AnalysisStates.UNTRACKED,
        "settings": settings,
        "created_on": datetime.utcnow(),
        "category": target_strictcontainer.category,
        "submitted": target_strictcontainer
    })

    analysis_info.to_file(AnalysisPaths.analysisjson(analysis_id))

    # Create an empty file for this new analysis. The state controller can
    # discover all newly created analyses this way after it receives a
    # notify message.
    Path(Paths.untracked(analysis_id)).touch()

def _is_correct_extrpath(extrpath):
    if not isinstance(extrpath, list):
        return False

    for entry in extrpath:
        if not isinstance(entry, str):
            return False

    return True

def find_extrpath_fileid(analysis_id, fileid):
    filemap = AnalysisPaths.filemap(analysis_id)
    if not os.path.isfile(filemap):
        raise SubmissionError("No filemap file exists. Cannot find exrtpath")

    try:
        with open(filemap, "r") as fp:
            filemap = json.load(fp)
    except json.JSONDecodeError as e:
        raise SubmissionError(
            f"Invalid filemap file. JSON decoding error: {e}"
        )

    fileid = str(fileid)
    if fileid not in filemap:
        raise SubmissionError("Given file id does not exist in filemap file")

    extrpath = filemap[fileid]
    if not _is_correct_extrpath(extrpath):
        raise SubmissionError(
            "Read filemap file entry is not a valid extrpath"
        )

    return extrpath

class SettingsVerifier:

    @staticmethod
    def verify_settings(settings, nodeinfos, limits):
        errs = []
        SettingsVerifier.check_limits(settings, limits, errs)
        if errs:
            raise SubmissionError(
                "One or more limits were exceeded: "
                f"{'. '.join(errs)}"
            )

        SettingsVerifier.verify_platforms(settings, nodeinfos, errs)
        if errs:
            raise SubmissionError(
                "One or more invalid settings were specified: "
                f"{'. '.join(errs)}"
            )

    @staticmethod
    def check_limits(settings, limits, error_list):
        if limits.get("max_timeout") and \
                settings.timeout > limits.get("max_timeout"):
            error_list.append(
                f"Timeout exceeds maximum timeout of "
                f"{limits.get('max_timeout')}"
            )

        if limits.get("max_priority") and \
                settings.priority > limits.get("max_priority"):
            error_list.append(
                f"Priority exceeds maximum priority of "
                f"{limits.get('max_priority')}"
            )

        if limits.get("max_platforms") and \
                len(settings.platforms) > limits.get("max_platforms"):
            error_list.append(
                f"Amount of platforms exceeds maximum of "
                f"{limits.get('max_platforms')}"
            )

    @staticmethod
    def verify_platforms(settings, nodeinfos, error_list):
        if not nodeinfos.has_nodes():
            error_list.append(
                "Cannot verify any machine or route settings. No node "
                "information is loaded"
            )
            return

        if settings.route and not settings.platforms:
            _, has_route, info = nodeinfos.find_support(None, settings.route)
            if not has_route:
                error_list.append(f"No node has route: {settings.route}")
            else:
                log.debug(
                    "Supporting node for route found", node=info.name,
                    route=settings.route
                )
            return

        for platform in settings.platforms:
            route = platform.settings.route or settings.route
            has_platform, has_route, info = nodeinfos.find_support(
                platform, route
            )
            if info:
                log.debug(
                    "Supporting node for platform and route combination found",
                    node=info.name, platform=platform, route=route
                )
                continue

            if not has_platform:
                error_list.append(f"No node has machine with: {platform}")
                continue

            if has_platform and route and not has_route:
                error_list.append(
                    f"No nodes have the combination of platform: "
                    f"{platform} and route {route}"
                )

class SettingsHelper:

    def __init__(self, default_settings, nodeinfos, limits):
        self._settings = deepcopy(default_settings)
        self._machine_lists = nodeinfos
        self._nodeinfos = nodeinfos
        self.limits = limits or {}

        self._key_handlers = {
            "timeout": self.set_timeout,
            "priority": self.set_priority,
            "manual": self.set_manual,
            "extrpath": self.set_extraction_path,
            "platforms": self.set_platforms_list,
            "route": self.set_route,
            "route_type": self.set_route_type,
            "route_option": self.set_route_option,
            "browser": self.set_browser,
            "command": self.set_command,
            "password": self.set_password,
            "orig_filename": self.set_orig_filename
        }

    def set_timeout(self, timeout):
        if timeout is None:
            return

        self._settings["timeout"] = timeout

    def set_priority(self, priority):
        if priority is None:
            return

        self._settings["priority"] = priority

    def set_manual(self, manual):
        if manual is None:
            return

        if not isinstance(manual, bool):
            raise SubmissionError("Manual must be a boolean")

        self._settings["manual"] = manual

    def _check_browser(self, browser):
        if not isinstance(browser, str):
            raise SubmissionError("Setting 'browser' must be a string")

        # Turn browser name into correct 'browser tag' format. Search
        # the available machines for this tag.
        tag = browser_to_tag(browser)

        if not find_in_lists(
                self._nodeinfos.all_machine_lists, tags=set([tag])
        ):
            raise SubmissionError(
                f"Browser {browser!r} not available. No machines with "
                f"tag {tag!r} exist."
            )

    def _check_route(self, route):
        if route and not isinstance(route, dict):
            raise SubmissionError("Setting 'route' must be a dictionary")

    def _read_command(self, command):
        if not command:
            return []

        if not isinstance(command, list):
            if not isinstance(command, str):
                raise SubmissionError(
                    "Setting 'command' must be a list of strings or a string"
                )

            return shlex.split(command)

        for arg in command:
            if not isinstance(arg, str):
                raise SubmissionError(f"Command args must be strings. {arg!r}")

        return command

    def set_extraction_path(self, extrpath):
        if extrpath is None:
            return

        if not _is_correct_extrpath(extrpath):
            raise SubmissionError(
                "The extraction path must be a list of one or more "
                "strings that represent the path(s) within the (nested) "
                "container"
            )

        self._settings["extrpath"] = extrpath

    def _check_platform_settings(self, settings):
        self._check_route(settings.get("route"))

    def _get_platform(self, platform_index):
        if not isinstance(platform_index, int) or platform_index < 0:
            raise SubmissionError("Platform index must be a positive integer")

        try:
            return self._settings["platforms"][platform_index]
        except IndexError:
            raise SubmissionError(f"No platform with index {platform_index}")

    def add_platform(self, platform, os_version="", tags=[], settings={}):
        if not platform:
            raise SubmissionError("Platform cannot be empty")

        if not isinstance(platform, str):
            raise SubmissionError(f"platform must be a string. {platform!r}")
        if not isinstance(os_version, str):
            raise SubmissionError(
                f"os_version must be a string. {os_version!r}"
            )

        if not isinstance(tags, list):
            raise SubmissionError(f"Tags must be a list of strings. {tags!r}")

        if settings and not isinstance(settings, dict):
            raise SubmissionError(
                f"Platform settings must be a dictionary. {settings!r}"
            )

        for tag in tags:
            if not isinstance(tag, str):
                raise SubmissionError(
                    f"Tags must be a list of strings. Invalid value: {tag!r}"
                )

        # Verify platform settings.
        self._check_platform_settings(settings)

        route = settings.get("route", {})
        if route:
            route = Route(**route)

        self._settings["platforms"].append(Platform(**{
            "platform": platform,
            "os_version": os_version,
            "tags": list(set(tags)),
            "settings": {
                "browser": settings.get("browser", ""),
                "route": route,
                "command": self._read_command(settings.get("command", []))
            }
        }))

    def add_platform_dict(self, platform_dict):
        err = """Platform dict must have {'platform': '<platform>',
        'os_version': '<optional version>'}"""
        if not isinstance(platform_dict, dict):
            raise SubmissionError(err)

        for k in ("platform", "os_version"):
            if k not in platform_dict:
                raise SubmissionError(err)

        self.add_platform(
            platform_dict["platform"],
            os_version=platform_dict["os_version"],
            tags=platform_dict.get("tags", []),
            settings=platform_dict.get("settings", {})
        )

    def set_route(self, route, platform_index=None):
        if not route:
            return

        self._check_route(route)
        try:
            route = Route(**route)
        except (TypeError, KeyError, ValueError) as e:
            raise SubmissionError(f"Invalid route format: {e}")

        if platform_index is None:
            self._settings["route"] = route
        else:
            self._get_platform(platform_index).set_route(route)

    def set_route_type(self, route_type, platform_index=None):
        if not isinstance(route_type, str):
            raise SubmissionError("Route type must be a string")

        if platform_index is None:
            self._settings["route"]["type"] = route_type
        else:
            self._get_platform(platform_index).set_route(type=route_type)

    def set_route_option(self, option, platform_index=None):
        if not isinstance(option, dict):
            raise SubmissionError("Route option must be a dictionary")

        if platform_index is None:
            self._settings["route"].setdefault("options", {}).update(option)
        else:
            self._get_platform(platform_index).settings.route.set_options(
                **option
            )

    def set_command(self, command, platform_index=None):
        command_args = self._read_command(command)
        if platform_index is None:
            self._settings["command"] = command_args
        else:
            self._get_platform(platform_index).set_command(command_args)

    def set_browser(self, browser, platform_index=None):
        if not browser:
            return

        self._check_browser(browser)
        if platform_index is None:
            self._settings["browser"] = browser

        else:
            self._get_platform(platform_index).set_browser(browser)

    def set_password(self, password):
        """Set the password used for archive unpacking"""
        if not isinstance(password, str):
            raise SubmissionError("Password must be a string")

        self._settings["password"] = password

    def set_orig_filename(self, use_orig):
        """Use the original filename, instead of the one identified by
        the identification stage."""
        if not isinstance(use_orig, bool):
            raise SubmissionError("The orig_filename value must be a boolean")

        self._settings["orig_filename"] = use_orig

    def add_machine_tag(self, tag, platform_index=None):
        """Add machine tag to all currently set platforms"""
        if not isinstance(tag, str):
            raise SubmissionError(f"Machine tag must be a string. {tag!r}")

        if platform_index is None:
            for platform in self._settings["platforms"]:
                if tag not in platform.tags:
                    platform.tags.append(tag)
        else:
            if not isinstance(platform_index, int) or platform_index < 0:
                raise SubmissionError(
                    "Platform index must be a positive integer"
                )

            self._get_platform(platform_index).tags.append(tag)

    def set_platforms_list(self, platforms):
        if not isinstance(platforms, list):
            raise SubmissionError(
                "Platforms must be a list of platform:<platform>,"
                "os_version:<version>, tags:<machine tag list> dictionaries"
            )

        for entry in platforms:
            self.add_platform_dict(entry)

    def set_setting(self, setting_key, value, platform_index=None):
        handler = self._key_handlers.get(setting_key)
        if not handler:
            raise SubmissionError(f"Unknown setting key: {setting_key!r}")

        if platform_index is None:
            handler(value)
        else:
            handler(value, platform_index=platform_index)

    def from_dict(self, settings_dict):
        for key, value in settings_dict.items():
            handler = self._key_handlers.get(key)
            if not handler:
                continue

            handler(value)

    @staticmethod
    def _add_browser_tags(settings):
        for platform in settings["platforms"]:
            browser = platform.settings["browser"] or settings["browser"]
            if browser:
                platform.tags.append(browser_to_tag(browser))

    @staticmethod
    def _make_routes(settings):
        """Make route objects from all dicts that were configured in parts
        /multiple function calls. This can happen with command line submission
        """
        route = settings.get("route")
        if route and isinstance(route, dict):
            settings["route"] = Route(**route)

        for platform in settings.get("platforms", []):
            route = platform.settings.route
            if route and isinstance(route, dict):
                platform["settings"]["route"] = Route(**route)

    def make_settings(self):
        try:
            settings_copy = deepcopy(self._settings)
            self._add_browser_tags(settings_copy)
            self._make_routes(settings_copy)
            s = Settings(**settings_copy)
            SettingsVerifier.verify_settings(s, self._nodeinfos, self.limits)
            return s
        except (ValueError, TypeError, AnalysisError) as e:
            raise SubmissionError(e)


class SettingsMaker:

    RELOAD_MINS = 5

    def __init__(self):
        self.nodeinfos = NodeInfos()
        self.default = {
            "timeout": 120,
            "priority": 1,
            "platforms": [],
            "manual": False,
            "dump_memory": False,
            "options": {},
            "enforce_timeout": True,
            "route": {},
            "command": [],
            "orig_filename": False,
            "password": "",
            "browser": "",
        }
        self.limits = {}
        self._nodeinfos_dump_path = None
        self._dmp_load_lock = RLock()

        self._last_modify_time = None
        self._last_reload = None

    def set_limits(self, limits_dict):
        self.limits.update(limits_dict)

    def set_defaults(self, settings_dict):
        route = settings_dict.get("route")
        # An empty route type means no default route. Change it
        # to an empty dict instead. This way it is easier to call set_defaults
        # with yaml settings values directly.
        if route and not route.get("type"):
            settings_dict["route"] = {}

        self.default.update(settings_dict)

    def _dump_modify_dt(self):
        return datetime.fromtimestamp(
                self._nodeinfos_dump_path.stat().st_mtime
            )

    def _should_reload_dump(self):
        if not self._last_reload or not self._last_modify_time:
            return True

        # Check if the dump file changed if the last reload is at least
        # RELOAD MINS minutes ago
        if datetime.utcnow() - self._last_reload < timedelta(
                minutes=self.RELOAD_MINS
        ):
            return False

        # Only reload if the dump file was actually modified since last check
        if self._dump_modify_dt() == self._last_modify_time:
            return False

        return True

    def _reload_if_needed(self):
        with self._dmp_load_lock:
            if not self._should_reload_dump():
                return

            self.reload_nodeinfo_dump()

    def set_nodesinfosdump_path(self, dump_path):
        dump_path = Path(dump_path)
        if not dump_path.is_file():
            raise SubmissionError(
                "Node info dump file does not exist. No node info has ever "
                "been loaded. Start Cuckoo to load node information from "
                "configuration file (or remote nodes). This will automatically"
                " create a node info dump."
            )

        self._nodeinfos_dump_path = dump_path

    def reload_nodeinfo_dump(self):
        """Loads and sets a node info dump made by the scheduler. Must be
        loaded before machine and route information can be verified and thus
         is require before being able to create new submissions."""
        if not self._nodeinfos_dump_path:
            raise SubmissionError(
                "No node info dump path has been configured"
            )

        if not self._nodeinfos_dump_path.is_file():
            raise SubmissionError(
                "Configured node infos dump path does not exist. "
            )

        with self._dmp_load_lock:
            self._last_modify_time = self._dump_modify_dt()
            self._last_reload = datetime.utcnow()
            self.nodeinfos = read_nodesinfos_dump(self._nodeinfos_dump_path)

    def available_platforms(self):
        self._reload_if_needed()
        return self.nodeinfos.get_platforms_versions()

    def available_routes(self):
        self._reload_if_needed()
        return self.nodeinfos.get_routes()

    def available_browsers(self):
        self._reload_if_needed()
        return self.nodeinfos.get_browsers()

    def new_settings(self, nodeinfos=None):
        """The node infos dump must have been loaded before if no
        nodeinfos is provided"""
        if nodeinfos:
            return SettingsHelper(self.default, nodeinfos, self.limits)

        self._reload_if_needed()
        return SettingsHelper(self.default, self.nodeinfos, self.limits)


# Global settings maker that can be initialized once and used by any module
# that imports it. Currently done like this to not have to load node info
# dumps and default settings from multiple places/modules within one process.
settings_maker = SettingsMaker()


def url(url, settings):
    analysis_id, folder_path = make_analysis_folder()
    _write_analysis(
        analysis_id, settings,
        SubmittedURL(category="url", url=force_valid_encoding(url))
    )
    return analysis_id

def file(filepath, settings, file_name=""):
    if file_name:
        file_name = force_valid_encoding(file_name)

    try:
        file_helper = File(filepath)
    except FileNotFoundError as e:
        raise SubmissionError(e)

    analysis_id, folder_path = make_analysis_folder()

    try:
        binary_helper = Binaries.store(Paths.binaries(), file_helper)
    except IOError as e:
        raise SubmissionError(e)

    binary_helper.symlink(AnalysisPaths.submitted_file(analysis_id))

    target_info = file_helper.to_dict()
    target_info["filename"] = file_name or file_helper.sha256
    target_info["category"] = "file"

    _write_analysis(analysis_id, settings, SubmittedFile(**target_info))
    return analysis_id

def notify():
    """Send a ping to the state controller to ask it to track all untracked
    analyses. Newly submitted analyses will not be tracked until the state
    controller receives a notify message."""
    try:
        StateControllerClient.notify(Paths.unix_socket("statecontroller.sock"))
    except ActionFailedError as e:
        raise SubmissionError(
            f"Failed to notify state controller of new analyses. "
            f"Is the main Cuckoo process running? {e}"
        )

def manual_set_settings(analysis_id, settings):
    state = get_state(analysis_id)
    if state != AnalysisStates.WAITING_MANUAL:
        raise SubmissionError(
            f"Settings can only be replaced if state "
            f"is {AnalysisStates.WAITING_MANUAL}. Current state is {state}"
        )

    try:
        StateControllerClient.manual_set_settings(
            Paths.unix_socket("statecontroller.sock"), analysis_id=analysis_id,
            settings_dict=settings.to_dict()
        )
    except ActionFailedError as e:
        raise SubmissionError(
            f"Failed to update settings for analysis. Is the main Cuckoo "
            f"process running? {e}"
        )
