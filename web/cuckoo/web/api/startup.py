# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import sys

from django.core.management import execute_from_command_line

from cuckoo.common import shutdown
from cuckoo.common.log import exit_error
from cuckoo.common.startup import (
    init_global_logging, load_configurations, init_database,
    init_elasticsearch, StartupError
)
from cuckoo.common.storage import cuckoocwd
from cuckoo.common.submit import load_machines_dump

import cuckoo.web.api

def set_path_settings():
    os.chdir(cuckoo.web.api.__path__[0])
    sys.path.insert(0, cuckoo.web.api.__path__[0])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cuckoo.web.api.settings")

def init_api(cuckoo_cwd, loglevel, logfile=""):
    if not cuckoocwd.exists(cuckoo_cwd):
        exit_error(
            f"Cuckoo CWD {cuckoo_cwd} does not yet exist. Run "
            f"'cuckoo createcwd' if this is the first time you are "
            f"running Cuckoo with this CWD path"
        )

    cuckoocwd.set(cuckoo_cwd)

    # Ensure any existing signal handlers for SIGINT/TERM are called after
    # any Cuckoo specific shutdown handlers.
    shutdown.set_call_original_handlers(call_original=True)
    try:
        init_global_logging(loglevel, logfile, warningsonly=["asyncio"])
        load_machines_dump(default={})
        load_configurations()
        init_database()
        init_elasticsearch(create_missing_indices=False)
    except StartupError as e:
        exit_error(f"Failed to initialize Cuckoo API. {e}")

    set_path_settings()

def start_api(host="127.0.0.1", port=8000, autoreload=False):
    args = ("cuckoo", "runserver", f"{host}:{port}")
    if not autoreload:
        args += ("--noreload",)

    execute_from_command_line(args)

def djangocommands(*args):
    execute_from_command_line(("cuckoo",) + args)
