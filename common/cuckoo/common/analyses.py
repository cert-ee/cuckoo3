# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os

from . import db, machines, targets
from .config import cfg
from .log import CuckooGlobalLogger
from .storage import (
    AnalysisPaths, delete_dirtree, delete_dir, split_analysis_id, todays_daydir
)
from .strictcontainer import Settings as _Settings, Analysis, Errors
from .utils import parse_bool

log = CuckooGlobalLogger(__name__)

class AnalysisError(Exception):
    pass

class AnalysisLocation:
    REMOTE = "remote"

class HumanStates:
    UNTRACKED = "Untracked"
    PENDING_IDENTIFICATION = "Pending identification"
    WAITING_MANUAL = "Waiting manual"
    PENDING_PRE = "Pending pre"
    TASKS_PENDING = "Task(s) pending"
    NO_SELECTED = "No selected target"
    FATAL_ERROR = "Fatal error"
    FINISHED = "Finished"

class States:
    UNTRACKED = "untracked"
    PENDING_IDENTIFICATION = "pending_identification"
    WAITING_MANUAL = "waiting_manual"
    PENDING_PRE = "pending_pre"
    TASKS_PENDING = "tasks_pending"
    NO_SELECTED = "no_selected"
    FATAL_ERROR = "fatal_error"
    FINISHED = "finished"

    _HUMAN = {
        PENDING_IDENTIFICATION: HumanStates.PENDING_IDENTIFICATION,
        WAITING_MANUAL: HumanStates.WAITING_MANUAL,
        PENDING_PRE: HumanStates.PENDING_PRE,
        NO_SELECTED: HumanStates.NO_SELECTED,
        FATAL_ERROR: HumanStates.FATAL_ERROR,
        TASKS_PENDING: HumanStates.TASKS_PENDING,
        FINISHED: HumanStates.FINISHED
    }

    @classmethod
    def to_human(cls, state):
        try:
            return cls._HUMAN[state]
        except KeyError:
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
        if self.machines and self.platforms:
            errors.append(
                "It is not possible to specify platforms and specific "
                "machines at the same time"
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
                tags = platform.get("tags", [])
                found = machines.find(
                    platform=os_name, os_version=os_version, tags=set(tags)
                )
                if not found:
                    err = f"No machine with platform: {os_name}"
                    if os_version:
                        err += f", os version: {os_version}"
                    if tags:
                        err += f", tags: {', '.join(tags)}"

                    errors.append(err)

        if errors:
            raise AnalysisError(
                f"One or more invalid settings were specified: "
                f"{'. '.join(errors)}"
            )

def exists(analysis_id):
    return os.path.isfile(AnalysisPaths.analysisjson(analysis_id))

def track_analyses(analysis_ids):
    untracked_analyses = []
    submitted_targets = []
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

        if analysis.category not in (targets.TargetCategories.FILE,
                                     targets.TargetCategories.URL):
            log.error(
                "Failed to track analysis", analysis_id=analysis_id,
                error=f"Unknown target category {analysis.category!r}"
            )
            continue

        untracked_analyses.append({
            "id": analysis_id,
            "kind": analysis.kind,
            "created_on": analysis.created_on,
            "priority": analysis.settings.priority,
            "state": States.PENDING_IDENTIFICATION
        })

        submitted_target = {
            "analysis_id": analysis_id,
            "category": analysis.category
        }
        if analysis.category == targets.TargetCategories.URL:
            submitted_target["target"] = analysis.submitted.url
        elif analysis.category == targets.TargetCategories.FILE:
            submitted_target.update({
                "target": analysis.submitted.filename,
                "media_type": analysis.submitted.media_type,
                "md5": analysis.submitted.md5,
                "sha1": analysis.submitted.sha1,
                "sha256": analysis.submitted.sha256,
                "sha512": ""
            })

        submitted_targets.append(submitted_target)
        tracked.append(analysis_id)

    ses = db.dbms.session()
    try:
        ses.bulk_insert_mappings(db.Analysis, untracked_analyses)
        ses.bulk_insert_mappings(db.Target, submitted_targets)
        ses.commit()
    finally:
        ses.close()

    return tracked

def db_set_remote(analyses):
    remote_analyses = []
    for analysis_id in analyses:

        # Ignore if not a valid analysis id
        try:
            split_analysis_id(analysis_id)
        except ValueError:
            continue

        remote_analyses.append({
            "id": analysis_id,
            "location": AnalysisLocation.REMOTE
        })

    ses = db.dbms.session()
    try:
        ses.bulk_update_mappings(db.Analysis, remote_analyses)
        ses.commit()
    finally:
        ses.close()


def track_imported(analysis):
    if analysis.state != States.FINISHED:
        raise AnalysisError(
            f"Imported analyses can only have the finished state."
        )

    target_dict = {
        "analysis_id": analysis.id,
        "category": analysis.category

    }
    if analysis.category == targets.TargetCategories.URL:
        target_dict["target"] = analysis.target.url
    elif analysis.category == targets.TargetCategories.FILE:
        target_dict.update({
            "target": analysis.target.filename,
            "media_type": analysis.target.media_type,
            "md5": analysis.target.md5,
            "sha1": analysis.target.sha1,
            "sha256": analysis.target.sha256,
            "sha512": ""
        })

    db_target = db.Target(**target_dict)
    db_analysis = db.Analysis(
        id=analysis.id, kind=Kinds.STANDARD, created_on=analysis.created_on,
        priority=analysis.settings.priority, state=analysis.state,
        score=analysis.score,
    )
    ses = db.dbms.session()
    try:
        ses.add(db_analysis)
        ses.add(db_target)
        ses.commit()
    finally:
        ses.close()

def merge_target_settings(analysis, target):
    if analysis.settings.machines:
        return

    autotag = cfg("cuckoo", "platform", "autotag")
    if analysis.settings.platforms:
        if not autotag:
            return

        if not target.machine_tags:
            return

        for platform in analysis.settings.platforms:
            platform["tags"].extend(target.machine_tags)
            platform["tags"] = list(set(platform["tags"]))

        analysis.update_settings(platforms=analysis.settings.platforms)

    elif target.platforms:
        # Only use the platforms specified in the config if more than one
        # platform was identified during the identification phase.
        allowed_multi = cfg("cuckoo", "platform", "multi_platform")
        all_identified = target.platforms

        settings_platforms = []

        for platform in all_identified:
            if len(all_identified) > 1:
                if platform["platform"] not in allowed_multi:
                    continue

            if autotag and target.machine_tags:
                platform["tags"] = target.machine_tags
            else:
                platform["tags"] = []

            settings_platforms.append(platform)

        analysis.update_settings(platforms=settings_platforms)

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
            "os_version": os_version or "",
            "tags": []
        }
        analysis.update_settings(platforms=[default])

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

def list_analyses(limit=None, offset=None, desc=True,
                  older_than=None, state=None, remote=None):
    ses = db.dbms.session()
    try:
        query = ses.query(db.Analysis)

        if older_than:
            query = query.filter(db.Analysis.created_on < older_than)

        if remote is not None:
            location = None
            if remote:
                location = AnalysisLocation.REMOTE
            query = query.filter_by(location=location)

        if state:
            query = query.filter_by(state=state)

        if desc:
            query = query.order_by(db.Analysis.created_on.desc())
        else:
            query = query.order_by(db.Analysis.created_on.asc())

        return query.limit(limit).offset(offset).all()

    # If a too large offset or limit is provided, some DBMSs (Such as SQLite),
    # can throw an overflow error because they cannot convert it.
    except OverflowError:
        return []
    finally:
        ses.close()

def dictlist(limit=None, offset=None, desc=True):
    if limit is not None and not isinstance(limit, int):
        try:
            limit = int(limit)
        except ValueError:
            raise TypeError("Limit must be an integer")

    if offset is not None and not isinstance(offset, int):
        try:
            offset = int(offset)
        except ValueError:
            raise TypeError("Offset must be an integer")

    if not isinstance(desc, bool):
        try:
            desc = parse_bool(desc)
        except (TypeError, ValueError):
            raise TypeError("Desc must be a boolean")

    return [
        a.to_dict() for a in list_analyses(
            limit=limit, offset=offset, desc=desc
        )
    ]

def get_fatal_errors(analysis_id):
    analysis = get_analysis(analysis_id)
    if not analysis.errors:
        return []

    fatalerrs = []
    for entry in analysis.errors.fatal:
        fatalerrs.append(entry["error"])

    return fatalerrs

def db_find_state(state):
    ses = db.dbms.session()
    try:
        return ses.query(db.Analysis).filter_by(state=state).all()
    finally:
        ses.close()

def db_find_location(analysis_id):
    ses = db.dbms.session()
    try:
        analysis = ses.query(
            db.Analysis.location
        ).filter_by(id=analysis_id).first()
        if not analysis:
            return None
        return analysis.location
    finally:
        ses.close()

def set_score(analysis, score):
    if score > analysis.score:
        analysis.score = score

def update_db_row(analysis_id, **kwargs):
    ses = db.dbms.session()
    try:
        ses.query(db.Analysis).filter_by(id=analysis_id).update(kwargs)
        ses.commit()
    finally:
        ses.close()

def write_changes(analysis):
    if not analysis.was_updated:
        return

    db_fields = {}
    for field in ("state", "score"):
        if field in analysis.updated_fields:
            db_fields[field] = analysis[field]

    # Verify updated_fields entries before dumping the analysis object. This
    # clears that list.
    update_target = False
    if "target" in analysis.updated_fields:
        update_target = True

    analysis.to_file_safe(AnalysisPaths.analysisjson(analysis.id))

    # Only perform database writes if the json dump is successful.
    if db_fields:
        update_db_row(analysis.id, **db_fields)

    if update_target:
        targets.update_target_row(analysis, analysis.target)


def delete_analysis_disk(analysis_id):
    daypart, _ = split_analysis_id(analysis_id)
    delete_dirtree(AnalysisPaths.path(analysis_id))

    # If the daydir is empty and it is not today, delete it.
    if daypart == todays_daydir():
        return

    daydir = AnalysisPaths.day(daypart)
    if len(os.listdir(daydir)) < 1:
        delete_dir(daydir)
