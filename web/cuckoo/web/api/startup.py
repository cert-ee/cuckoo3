# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import sys

import django
from django.core.management import execute_from_command_line
from django.db.migrations.executor import MigrationExecutor
from django.db import connections, DEFAULT_DB_ALIAS

from cuckoo.common import shutdown
from cuckoo.common.log import exit_error
from cuckoo.common.startup import (
    init_global_logging, load_configuration, init_database, StartupError
)
from cuckoo.common.storage import cuckoocwd, Paths, CWD_ENVVAR, CWDError
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

    try:
        cuckoocwd.set(cuckoo_cwd)
    except CWDError as e:
        exit_error(f"Failed to set Cuckoo working directory: {e}")

    # Ensure any existing signal handlers for SIGINT/TERM are called after
    # any Cuckoo specific shutdown handlers.
    shutdown.set_call_original_handlers(call_original=True)

    load_app()
    try:
        init_global_logging(loglevel, logfile)
        nodeinfos_dump = Paths.nodeinfos_dump()
        if nodeinfos_dump.is_file():
            settings_maker.set_nodesinfosdump_path(nodeinfos_dump)

        load_configuration("web.yaml", subpkg="web")
        load_configuration("analysissettings.yaml")
        settings_maker.set_limits(cfg("analysissettings.yaml", "limits"))
        settings_maker.set_defaults(cfg("analysissettings.yaml", "default"))
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

def init_and_get_wsgi():
    import logging
    from cuckoo.common.log import disable_console_colors, name_to_level
    levelname = os.environ.get("CUCKOO_LOGLEVEL")
    if not levelname:
        loglevel = logging.DEBUG
    else:
        try:
            loglevel = name_to_level(levelname)
        except ValueError as e:
            exit_error(f"Invalid log level name. {e}")

    cwd_path = os.environ.get(CWD_ENVVAR)
    if not cwd_path:
        exit_error(
            f"Cannot start. Environment variable '{CWD_ENVVAR}' must "
            f"contain path to Cuckoo CWD."
        )

    # Disable console colors, because log files for services such as uWSGI
    # capture console logs. Color formatting characters can make the log file
    # unreadable.
    disable_console_colors()
    init_api(cwd_path, loglevel)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cuckoo.web.api.settings')
    from django.core.wsgi import get_wsgi_application
    return get_wsgi_application()
