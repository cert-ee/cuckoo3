# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os.path
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from .analyses import (
    Kinds as AnalysisKinds, AnalysisError, Settings, get_state,
    States as AnalysisStates
)
from .clients import StateControllerClient, ActionFailedError
from .machines import read_machines_dump, set_machines_dump
from .storage import File, Binaries, Paths, AnalysisPaths, make_analysis_folder
from .strictcontainer import Analysis, SubmittedFile

class SubmissionError(Exception):
    pass


def _write_analysis(analysis_id, settings, target_strictcontainer):
    analysis_info = Analysis(**{
        "id": analysis_id,
        "kind": AnalysisKinds.STANDARD,
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

_DEFAULT_SETTINGS = {
    "timeout": 120,
    "priority": 1,
    "platforms": [],
    "machines": [],
    "machine_tags": [],
    "manual": False,
    "dump_memory": False,
    "options": {},
    "enforce_timeout": True
}

def load_machines_dump():
    """Loads and sets a machines dump made by the MachineryManager. Must be
    loaded before machine information can be verified and thus is required
    before being able to create new submissions."""
    dump_path = Path(Paths.machinestates())
    if not dump_path.is_file():
        raise SubmissionError(
            "Machine dump does not exist. No machines have ever been loaded. "
            "Start Cuckoo to load these from the machine configurations and "
            "automatically create machine dumps."
        )

    dump = read_machines_dump(dump_path)
    set_machines_dump(dump)

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

    extrpath = filemap.get(str(fileid))
    if not extrpath:
        raise SubmissionError("Given file id does not exist in filemap file")

    if not _is_correct_extrpath(extrpath):
        raise SubmissionError(
            "Read filemap file entry is not a valid extrpath"
        )

    return extrpath

class SettingsMaker:

    def __init__(self):
        self._settings = deepcopy(_DEFAULT_SETTINGS)

    def set_timeout(self, timeout):
        if timeout is None:
            return
        self._settings["timeout"] = timeout

    def set_priority(self, priority):
        if priority is None:
            return

        self._settings["priority"] = priority

    def set_manual(self, manual):
        self._settings["manual"] = manual

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

    def add_platform(self, platform, os_version=""):
        if not isinstance(platform, str):
            raise SubmissionError(f"platform must be a string. {platform!r}")
        if not isinstance(os_version, str):
            raise SubmissionError(
                f"os_version must be a string. {os_version!r}"
            )

        self._settings["platforms"].append(
            {"platform": platform, "os_version": os_version}
        )

    def add_platform_dict(self, platform_osversion):
        err = """Platform dict must be dict {'platform': '<platform>',
        'os_version': '<optional version>'}"""
        if not isinstance(platform_osversion, dict):
            raise SubmissionError(err)

        for k in ("platform", "os_version"):
            if k not in platform_osversion:
                raise SubmissionError(err)

        self.add_platform(
            platform_osversion["platform"], platform_osversion["os_version"]
        )

    def set_platforms_list(self, platforms):
        if not isinstance(platforms, list):
            raise SubmissionError(
                "Platforms must be a list of platform:<platform>,"
                "os_version:<version> dictionaries"
            )

        for entry in platforms:
            self.add_platform_dict(entry)

    def add_machine_tag(self, tag):
        if not isinstance(tag, str):
            raise SubmissionError(f"tag must be a string. {tag!r}")

        tags = self._settings["machine_tags"]
        if tag not in tags:
            tags.append(tag)


    def make_settings(self):
        try:
            return Settings(**self._settings)
        except (ValueError, TypeError, AnalysisError) as e:
            raise SubmissionError(e)


def file(filepath, settings, file_name=""):
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
