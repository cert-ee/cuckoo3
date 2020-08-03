# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from jinja2.environment import Environment

from .filters import filters

def environment(**kwargs):
    env = Environment(**kwargs)
    env.filters.update(filters)
    return env
