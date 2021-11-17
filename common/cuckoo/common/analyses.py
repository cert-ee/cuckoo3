# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from copy import deepcopy
import json
import os

from . import db, targets
from .config import cfg
from .log import CuckooGlobalLogger
from .storage import (
    AnalysisPaths, delete_dirtree, delete_dir, split_analysis_id, todays_daydir
)
from .strictcontainer import Settings as _Settings, Analysis, Errors, Platform
from .utils import parse_bool, browser_to_tag

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
        errors = []
        if self.priority < 1:
            errors.append("Priority must be 1 at least")

        if errors:
            raise AnalysisError(
                f"One or more invalid settings were specified: "
                f"{'. '.join(errors)}"
            )

def exists(analysis_id):
    return AnalysisPaths.analysisjson(analysis_id).is_file()

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
            "Imported analyses can only have the finished state."
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

def overwrite_platforms(analysis, platforms):
    analysis.update_settings(platforms=platforms)

def _update_existing_platforms(analysis, pre):
    """Update an existing platform list with machine tags if auto tagging
    is enabled. Does not modify the start command. For existing platforms this
    is already done in the pre processing stage."""
    if not cfg("cuckoo", "platform", "autotag"):
        return analysis.settings.platforms

    if not pre.target.machine_tags:
        return analysis.settings.platforms

    for platform in analysis.settings.platforms:
        # Add automatically determined (dependency) machine tags for each
        # platform.
        platform.tags.extend(pre.target.machine_tags)

        # Ensure tags list is unique.
        platform.tags = list(set(platform.tags))

    return analysis.settings.platforms

def _platforms_from_target(analysis, pre):
    """Determine one or more platforms to create tasks for by using the
    identified platforms the target can run on. Use the pre command map to
    determine how a target should be started for a specific platform."""
    autotag = cfg("cuckoo", "platform", "autotag")
    versions_dict = cfg("analysissettings", "platform", "versions")
    allowed_multi = cfg("analysissettings", "platform", "multi_platform")

    browser_tag = ""
    if analysis.settings.browser:
        browser_tag = browser_to_tag(analysis.settings.browser)

    # See if we should add a platform for each identified potential platform
    # for this target.
    auto_platforms = []
    for target_platform in pre.target.platforms:
        # In case multiple potential platforms are identified, only choose
        # those that are in the 'multi_platform' setting of the analysis
        # settings.
        if len(pre.target.platforms) > 1:
            if target_platform["platform"] not in allowed_multi:
                continue

        platform_copy = deepcopy(target_platform)
        platform_copy["tags"] = []
        # Add a browser tag for the analysis settings browser if no
        # platform browser was chosen.
        if browser_tag:
            platform_copy["tags"].append(browser_tag)

        if autotag and pre.target.machine_tags:
            platform_copy["tags"].extend(pre.target.machine_tags)

        # Create a platform entry for each specified platform version in
        # analysis settings. Otherwise just create an entry without a version.
        if platform_copy["platform"] in versions_dict:
            for version in versions_dict[platform_copy["platform"]]:
                version_copy = deepcopy(platform_copy)
                version_copy["os_version"] = version
                platform_obj = Platform(**version_copy)
                # Set the command to the automatically determined launch
                # command for the specific platform
                platform_obj.set_command(
                    pre.command.get(platform_obj.platform, [])
                )
                auto_platforms.append(platform_obj)
        else:
            platform_obj = Platform(**platform_copy)
            # Set the command to the automatically determined launch
            # command for the specific platform
            platform_obj.set_command(
                pre.command.get(platform_obj.platform, [])
            )
            auto_platforms.append(platform_obj)

    return auto_platforms

def _get_fallback_platforms(analysis, pre):
    """Uses the fallback platform settings and versions to determine one or
    more platforms to create tasks for. Use the pre command map to
    determine how a target should be started for a specific platform."""
    fallback_platforms = cfg(
        "analysissettings", "platform", "fallback_platforms"
    )
    versions_dict = cfg("analysissettings", "platform", "versions")
    browser_tag = ""
    if analysis.settings.browser:
        browser_tag = browser_to_tag(analysis.settings.browser)

    settings_platforms = []
    for fallback_platform in fallback_platforms:
        versions = versions_dict.get(fallback_platform)
        if not versions:
            platform_obj = Platform(
                platform=fallback_platform,
                tag=[] if not browser_tag else [browser_tag]
            )
            # Set the command to the automatically determined launch
            # command for the specific platform
            platform_obj.set_command(
                pre.command.get(platform_obj.platform, [])
            )
            settings_platforms.append(platform_obj)
        else:
            # Create a platform entry for each version of the fallback platform
            for os_version in versions:
                platform_obj = Platform(
                    platform=fallback_platform, os_version=os_version,
                    tag=[] if not browser_tag else [browser_tag]
                )
                # Set the command to the automatically determined launch
                # command for the specific platform
                platform_obj.set_command(
                    pre.command.get(platform_obj.platform, [])
                )
                settings_platforms.append(platform_obj)

    for platform in settings_platforms:
        log.debug(
            "No platform given or identified. Using fallback_platform",
            analysis_id=analysis.id, platform=platform.platform,
            os_version=platform.os_version
        )

    return settings_platforms

def determine_final_platforms(analysis, pre):
    """Determine and set the final platforms list that will be used to
    create tasks for an analysis."""
    # Merge target settings with submission existing specified platform
    # settings
    if analysis.settings.platforms:
        platforms = _update_existing_platforms(analysis, pre)
    # Choose one or more platforms based on identified platform(s). This is
    # done when no platforms are supplied on submission.
    elif pre.target.platforms:
        platforms = _platforms_from_target(analysis, pre)
    # Use the default platform from the settings. This is done when no
    # platform is supplied on submission and no platform is identified.
    else:
        platforms = _get_fallback_platforms(analysis, pre)

    overwrite_platforms(analysis, platforms)

def merge_errors(analysis, error_container):
    if analysis.errors:
        analysis.errors.merge_errors(error_container)
    else:
        analysis.errors = error_container

def merge_processing_errors(analysis):
    errpath = AnalysisPaths.processingerr_json(analysis.id)
    if not errpath.is_file():
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
    if not treepath.is_file():
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

def count_submission(start=None, end=None):
    ses = db.dbms.session()
    try:
        q = ses.query(db.Analysis)
        if start and end:
            q = q.filter(
                db.Analysis.created_on>=start, db.Analysis.created_on<=end
            )
        return q.count()
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

    # If the daydir is today, never delete it.
    if daypart == todays_daydir():
        return

    daydir = AnalysisPaths.day(daypart)
    # Delete day dir if it is empty
    if sum(1 for _ in daydir.iterdir()) < 1:
        delete_dir(daydir)
