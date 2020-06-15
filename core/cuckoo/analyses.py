# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.processing import typehelpers

from . import db, machinery
from cuckoo.common.storage import AnalysisPaths

class AnalysisError(Exception):
    pass


class Settings(typehelpers.Settings):

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
                if not machinery.find(platform, tags=set(self.machine_tags)):
                    err = f"No machine with platform: {platform}"
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
            analysis = typehelpers.Analysis.from_file(info_path)
        except (ValueError, TypeError) as e:
            raise AnalysisError(f"Failed to load analysis.json: {e}")

        untracked_analyses.append({
            "id": analysis_id,
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
