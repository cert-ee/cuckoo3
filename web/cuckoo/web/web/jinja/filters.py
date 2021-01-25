# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from datetime import datetime

from cuckoo.common.analyses import States as AnalysisStates
from cuckoo.common.task import States as TaskStates

def do_formatdatetime(value, fmt="%Y-%m-%d %H:%M"):
    return value.strftime(fmt)

def do_formatisodatetime(value, fmt="%Y-%m-%d %H:%M"):
    millis_index = value.find(".")

    # Ignore the milliseconds. They would cause a value error and might
    # not always be present.
    if millis_index:
        value = value[:millis_index]

    return do_formatdatetime(
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S"), fmt
    )

def do_humanstate(value):
    return AnalysisStates.to_human(value)

def do_taskstatehuman(value):
    return TaskStates.to_human(value)

filters = {
    "formatdatetime": do_formatdatetime,
    "formatisodatetime": do_formatisodatetime,
    "humanstate": do_humanstate,
    "taskstatehuman": do_taskstatehuman
}
