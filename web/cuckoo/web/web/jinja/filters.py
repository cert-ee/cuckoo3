# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import dateutil.parser

from cuckoo.common.analyses import States as AnalysisStates
from cuckoo.common.config import cfg
from cuckoo.common.task import States as TaskStates

_enabled_features = {
    "search": cfg(
        "web.yaml", "elasticsearch", "web_search", "enabled", subpkg="web"
    ),
    "statistics": cfg(
        "web.yaml", "elasticsearch", "statistics", "enabled", subpkg="web"
    )
}

def do_formatdatetime(value, fmt="%Y-%m-%d %H:%M"):
    return value.strftime(fmt)

def do_formatisodatetime(value, fmt="%Y-%m-%d %H:%M"):
    try:
        return do_formatdatetime(dateutil.parser.parse(value), fmt)
    except dateutil.parser.ParserError:
        return value

def do_humanstate(value):
    return AnalysisStates.to_human(value)

def do_taskstatehuman(value):
    return TaskStates.to_human(value)

def feature_enabled(name):
    return _enabled_features.get(name, True)

filters = {
    "formatdatetime": do_formatdatetime,
    "formatisodatetime": do_formatisodatetime,
    "humanstate": do_humanstate,
    "taskstatehuman": do_taskstatehuman,
    "feature_enabled": feature_enabled
}
