# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2.environment import Environment

from .filters import filters

_globals = {
    "static": staticfiles_storage.url,
    "url": reverse,
}

def environment(**kwargs):
    env = Environment(**kwargs)
    env.filters.update(filters)
    env.globals.update(_globals)
    return env
