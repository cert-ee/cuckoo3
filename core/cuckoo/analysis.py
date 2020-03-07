# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.processing import typehelpers

from . import db
from .storage import AnalysisPaths

class AnalysisError(Exception):
    pass

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
