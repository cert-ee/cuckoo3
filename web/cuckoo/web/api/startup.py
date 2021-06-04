# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import sys

import django
from django.core.management import execute_from_command_line
from django.db.migrations.executor import MigrationExecutor
from django.db import connections, DEFAULT_DB_ALIAS

from cuckoo.common import shutdown
from cuckoo.common.log import exit_error
from cuckoo.common.startup import (
    init_global_logging, load_configurations, init_database, StartupError
)
from cuckoo.common.storage import cuckoocwd, Paths
from cuckoo.common.submit import settings_maker
from cuckoo.common.result import retriever
from cuckoo.common.clients import APIClient
from cuckoo.common.config import cfg

import cuckoo.web.api

def _djangodb_migrations_required():
    connection = connections[DEFAULT_DB_ALIAS]
    connection.prepare_database()
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    return executor.migration_plan(targets)

def load_app():
    set_path_settings()
    django.setup()
    if _djangodb_migrations_required():
        exit_error(
            "Django database migrations required. "
            f"Run 'cuckoo --cwd {cuckoocwd.root} api djangocommand migrate' "
            f"to perform the migration."
        )

def set_path_settings():
    os.chdir(cuckoo.web.api.__path__[0])
    sys.path.insert(0, cuckoo.web.api.__path__[0])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cuckoo.web.api.settings")

def _init_remote_storage():
    api = APIClient(
        cfg("web.yaml", "remote_storage", "api_url", subpkg="web"),
        cfg("web.yaml", "remote_storage", "api_key", subpkg="web")
    )
    retriever.set_api_client(api)

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

    load_app()
    try:
        init_global_logging(loglevel, logfile)
        machines_dump = Paths.machinestates()
        if machines_dump.is_file():
            settings_maker.set_machinesdump_path(machines_dump)

        load_configurations()
        init_database()
        if cfg("web.yaml", "remote_storage", "enabled", subpkg="web"):
            _init_remote_storage()
    except StartupError as e:
        exit_error(f"Failed to initialize Cuckoo API. {e}")


def start_api(host="127.0.0.1", port=8000, autoreload=False):
    args = ("cuckoo", "runserver", f"{host}:{port}")
    if not autoreload:
        args += ("--noreload",)

    execute_from_command_line(args)

def djangocommands(*args):
    execute_from_command_line(("cuckoo",) + args)
