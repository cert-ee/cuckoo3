# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.config import cfg
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.storage import AnalysisPaths
from cuckoo.common.strictcontainer import (
    Settings, Analysis, Identification, Pre, Errors
)

from . import db, machinery

log = CuckooGlobalLogger(__name__)

class AnalysisError(Exception):
    pass


class Settings(Settings):

    def check_constraints(self):
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
                machinery.get_by_name(machine)
            except machinery.MachineDoesNotExistError:
                errors.append(f"Machine with name '{machine}' does not exist")

        if self.platforms:
            for platform in self.platforms:
                os_name = platform.get("platform")
                os_version = platform.get("os_version")
                found = machinery.find(
                    platform=os_name, os_version=os_version,
                    tags=set(self.machine_tags)
                )
                if not found:
                    err = f"No machine with platform: {os_name} {os_version}"
                    if self.machine_tags:
                        err += f" and tags {self.machine_tags}"

                    errors.append(err)

        elif self.machine_tags:
            if not machinery.find(tags=set(self.machine_tags)):
                errors.append(f"No machine with tags: {self.machine_tags}")

        if errors:
            raise AnalysisError(
                f"One or more invalid settings were specified: "
                f"{'. '.join(errors)}"
            )

def track_analyses(analysis_ids):

    untracked_analyses = []
    for analysis_id in analysis_ids:
        info_path = AnalysisPaths.analysisjson(analysis_id)

        try:
            analysis = Analysis.from_file(info_path)
        except (ValueError, TypeError) as e:
            raise AnalysisError(f"Failed to load analysis.json: {e}")

        untracked_analyses.append({
            "id": analysis_id,
            "kind": db.AnalysisKinds.STANDARD,
            "created_on": analysis.created_on,
            "priority": analysis.settings.priority,
            "state": db.AnalysisStates.PENDING_IDENTIFICATION
        })

    ses = db.dbms.session()
    try:
        ses.bulk_insert_mappings(db.Analysis, untracked_analyses)
        ses.commit()
    finally:
        ses.close()

    return True

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

def merge_analysis_errors(analysis_id, error_container):
    analysisjson_path = AnalysisPaths.analysisjson(analysis_id)
    analysis = Analysis.from_file(analysisjson_path)
    if analysis.errors:
        analysis.errors.merge_errors(error_container)
    else:
        analysis.errors = error_container

    analysis.to_file_safe(analysisjson_path)

def merge_ident_errors(analysis_id):
    errpath = AnalysisPaths.processingerr_json(analysis_id)
    if not os.path.exists(errpath):
        return

    identpath = AnalysisPaths.identjson(analysis_id)
    ident = Identification.from_file(identpath)
    errs = Errors.from_file(errpath)
    if ident.errors:
        ident.errors.merge_errors(errs)
    else:
        ident.errors = errs

    # Update the identification json file
    ident.to_file_safe(identpath)
    os.remove(errpath)

def merge_pre_errors(analysis_id):
    errpath = AnalysisPaths.processingerr_json(analysis_id)
    if not os.path.exists(errpath):
        return

    prepath = AnalysisPaths.prejson(analysis_id)
    pre = Pre.from_file(prepath)
    errs = Errors.from_file(errpath)
    if pre.errors:
        pre.errors.merge_errors(errs)
    else:
        pre.errors = errs

    # Update the pre json file
    pre.to_file_safe(prepath)
    os.remove(errpath)
