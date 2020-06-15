# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import pathlib
from datetime import datetime

from cuckoo.processing import typehelpers

from cuckoo.common.ipc import message_unix_socket
from cuckoo.common.storage import (
    Binaries, make_analysis_folder, Paths, AnalysisPaths
)

class SubmissionError(Exception):
    pass


def write_analysis_info(analysis_id, settings, submitted_target):

    analysis_info = typehelpers.Analysis(**{
        "id": analysis_id,
        "settings": settings,
        "created_on": datetime.utcnow(),
        "category": submitted_target.category,
        "submitted": submitted_target
    })

    analysis_info.to_file(AnalysisPaths.analysisjson(analysis_id))
    pathlib.Path(Paths.untracked(analysis_id)).touch()

def file(file_helper, settings, file_name=None):
    try:
        binary_path = Binaries.store(
            Paths.binaries(), file_helper
        )
    except IOError as e:
        raise SubmissionError(e)

    analysis_id, folder_path = make_analysis_folder()
    os.symlink(binary_path, os.path.join(folder_path, "binary"))


    target_info = file_helper.to_dict()
    target_info["filename"] = file_name or file_helper.sha256
    target_info["category"] = "file"

    submitted_file = typehelpers.SubmittedFile(**target_info)
    write_analysis_info(analysis_id, settings, submitted_file)

    return analysis_id

def notify():
    message_unix_socket(
        Paths.unix_socket("statecontroller.sock"), {"subject": "tracknew"}
    )
