# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import pathlib
from datetime import datetime

from cuckoo.processing import typehelpers

from . import machinery
from .ipc import message_unix_socket
from .storage import Binaries, make_analysis_folder, Paths, AnalysisPaths

class SubmissionError(Exception):
    pass


class Settings(typehelpers.Settings):
    
    def __init__(self, **kwargs):
        try:
            super(Settings, self).__init__(**kwargs)
        except (ValueError, TypeError) as e:
            raise SubmissionError(e).with_traceback(e.__traceback__)

        self.check_constraints()

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
            if not machinery.name_exists(machine):
                errors.append(f"Machine with name '{machine}' does not exist")

        if errors:
            raise SubmissionError(
                f"One or more invalid settings were specified: "
                f"{'. '.join(errors)}"
            )


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
        Paths.unix_socket("controller.sock"), {"subject": "tracknew"}
    )
