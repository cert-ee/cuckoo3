# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common.analyses import States

def do_formatdatetime(value, fmt="%Y-%m-%d %H:%M"):
    return value.strftime(fmt)

def do_humanstate(value):
    return States.to_human(value)

filters = {
    "formatdatetime": do_formatdatetime,
    "humanstate": do_humanstate
}
