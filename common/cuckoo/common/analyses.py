# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import json

from . import db, machines
from .config import cfg
from .log import CuckooGlobalLogger
from .storage import AnalysisPaths
from .strictcontainer import (
    Settings as _Settings, Analysis, Identification, Pre, Errors
)

log = CuckooGlobalLogger(__name__)

class AnalysisError(Exception):
    pass

class HumanStates:
    PENDING_IDENTIFICATION = "Pending identification"
    WAITING_MANUAL = "Waiting manual"
    PENDING_PRE = "Pending pre"
    COMPLETED_PRE = "Completed pre"
    NO_SELECTED = "No selected target"
    FATAL_ERROR = "Fatal error"

class States:
    PENDING_IDENTIFICATION = "pending_identification"
    WAITING_MANUAL = "waiting_manual"
    PENDING_PRE = "pending_pre"
    COMPLETED_PRE = "completed_pre"
    NO_SELECTED = "no_selected"
    FATAL_ERROR = "fatal_error"

    _HUMAN = {
        PENDING_IDENTIFICATION: HumanStates.PENDING_IDENTIFICATION,
        WAITING_MANUAL: HumanStates.WAITING_MANUAL,
        PENDING_PRE: HumanStates.PENDING_PRE,
        COMPLETED_PRE: HumanStates.COMPLETED_PRE,
        NO_SELECTED: HumanStates.NO_SELECTED,
        FATAL_ERROR: HumanStates.FATAL_ERROR
    }

    @classmethod
    def to_human(cls, state):
        try:
            return cls._HUMAN[state]
        except KeyError as e:
            raise AnalysisError(
                f"No human readable version for state {state!r} exists"
            )

class Kinds:
    STANDARD = "standard"


class Settings(_Settings):

    def check_constraints(self):
        if not machines.machines_loaded():
            raise AnalysisError(
                "Cannot verify any machine settings. No machines are loaded."
            )

        errors = []
        if self.priority < 1:
            errors.append("Priority must be 1 at least")
        if self.machines and (self.platforms or self.machine_tags):
            errors.append(
                "It is not possible to specify specific machines and "
                "platforms or tags at the same time"
            )
        for machine in self.machines:
            try:
                machines.get_by_name(machine)
            except KeyError:
                errors.append(f"Machine with name '{machine}' does not exist")

        if self.platforms:
            for platform in self.platforms:
                os_name = platform.get("platform")
                os_version = platform.get("os_version")
                found = machines.find(
                    platform=os_name, os_version=os_version,
                    tags=set(self.machine_tags)
                )
                if not found:
                    err = f"No machine with platform: {os_name} {os_version}"
                    if self.machine_tags:
                        err += f" and tags {self.machine_tags}"

                    errors.append(err)

        elif self.machine_tags:
            if not machines.find(tags=set(self.machine_tags)):
                errors.append(f"No machine with tags: {self.machine_tags}")

        if errors:
            raise AnalysisError(
                f"One or more invalid settings were specified: "
                f"{'. '.join(errors)}"
            )

def exists(analysis_id):
    return os.path.isfile(AnalysisPaths.analysisjson(analysis_id))

def track_analyses(analysis_ids):

    untracked_analyses = []
    tracked = []
    for analysis_id in analysis_ids:
        info_path = AnalysisPaths.analysisjson(analysis_id)

        try:
            analysis = Analysis.from_file(info_path)
        except (ValueError, TypeError, FileNotFoundError) as e:
            log.error(
                "Failed to track analysis", analysis_id=analysis_id, error=e
            )
            continue

        untracked_analyses.append({
            "id": analysis_id,
            "kind": analysis.kind,
            "created_on": analysis.created_on,
            "priority": analysis.settings.priority,
            "state": States.PENDING_IDENTIFICATION
        })
        tracked.append(analysis_id)

    ses = db.dbms.session()
    try:
        ses.bulk_insert_mappings(db.Analysis, untracked_analyses)
        ses.commit()
    finally:
        ses.close()

    return tracked

def overwrite_settings(analysis, settings):
    analysis.settings = settings

def update_settings(analysis, **kwargs):
    analysis.settings.update(kwargs)

def merge_settings_ident(analysis, identification):
    if analysis.settings.machines:
        return False

    was_updated = False
    use_autotag = cfg("cuckoo", "platform", "autotag")
    if use_autotag and identification.target.machine_tags:
        update_settings(
            analysis, machine_tags=identification.target.machine_tags
        )
        was_updated = True

    if analysis.settings.platforms:
        return was_updated

    if identification.target.platforms:
        # Only use the platforms specified in the config if more than one
        # platform was identified during the identification phase.
        if len(identification.target.platforms) > 1:
            allowed_ident = cfg("cuckoo", "platform", "multi_platform")
            for platform in identification.target.platforms[:]:
                if platform["platform"] not in allowed_ident:
                    identification.target.platforms.remove(platform)

        update_settings(analysis, platforms=identification.target.platforms)
        was_updated = True

    else:
        platform = cfg("cuckoo", "platform", "default_platform", "platform")
        os_version = cfg(
            "cuckoo", "platform", "default_platform", "os_version"
        )

        log.debug(
            "No platform given or identified. Using default_platform.",
            analysis_id=analysis.id, platform=platform, os_version=os_version
        )
        default = {
            "platform": platform,
            "os_version": os_version
        }
        update_settings(
            analysis, platforms=[default]
        )
        was_updated = True

    return was_updated

def merge_errors(analysis, error_container):
    if analysis.errors:
        analysis.errors.merge_errors(error_container)
    else:
        analysis.errors = error_container

def merge_processing_errors(analysis):
    errpath = AnalysisPaths.processingerr_json(analysis.id)
    if not os.path.exists(errpath):
        return

    merge_errors(analysis, Errors.from_file(errpath))

    os.remove(errpath)

def set_final_target(analysis, target):
    analysis.target = target

def get_state(analysis_id):
    ses = db.dbms.session()
    try:
        analysis = ses.query(
            db.Analysis.state
        ).filter_by(id=analysis_id).first()

        if not analysis:
            return None

        return analysis.state
    finally:
        ses.close()

def get_analysis(analysis_id):
    if not exists(analysis_id):
        raise AnalysisError(
            f"Analysis JSON file for {analysis_id} does not exist."
        )

    try:
        return Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
    except ValueError as e:
        raise AnalysisError(f"Failed to read analysis JSON file. {e}")

def get_filetree_fp(analysis_id):
    treepath = AnalysisPaths.filetree(analysis_id)
    if not os.path.isfile(treepath):
        raise AnalysisError("Filetree JSON file does not exist")

    return open(treepath, "r")

def get_filetree_dict(analysis_id):
    fp = get_filetree_fp(analysis_id)
    try:
        return json.load(fp)
    except json.JSONDecodeError as e:
        raise AnalysisError(
            f"Failed to read filetree JSON. JSON decoding error: {e}"
        )
    finally:
        fp.close()

def list(limit=None):
    ses = db.dbms.session()
    try:
        return ses.query(db.Analysis).limit(limit).order_by(
            db.Analysis.created_on
        ).all()
    finally:
        ses.close()

def dictlist(limit=None):
    return [a.to_dict() for a in list(limit)]
