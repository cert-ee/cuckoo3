# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import sys

from django.core.management import execute_from_command_line

from cuckoo.common import shutdown
from cuckoo.common.log import exit_error, name_to_level
from cuckoo.common.startup import (
    init_global_logging, load_configuration, init_database,
    init_elasticsearch, StartupError
)
from cuckoo.common.storage import cuckoocwd, Paths, CWD_ENVVAR, CWDError
from cuckoo.common.submit import settings_maker
from cuckoo.common.result import retriever
from cuckoo.common.clients import APIClient
from cuckoo.common.resultstats import chartdata_maker, StatisticsError
from cuckoo.common.config import cfg

import cuckoo.web

def set_path_settings():
    os.chdir(cuckoo.web.__path__[0])
    sys.path.insert(0, cuckoo.web.__path__[0])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cuckoo.web.web.settings")

def _init_remote_storage():
    api = APIClient(
        cfg("web.yaml", "remote_storage", "api_url", subpkg="web"),
        cfg("web.yaml", "remote_storage", "api_key", subpkg="web")
    )
    retriever.set_api_client(api)

def _init_elasticsearch_web():
    hosts = cfg("web.yaml", "elasticsearch", "hosts", subpkg="web")
    indices = cfg(
        "web.yaml", "elasticsearch", "indices", "names", subpkg="web"
    )
    max_window = cfg(
        "web.yaml", "elasticsearch", "max_result_window", subpkg="web"
    )

    init_elasticsearch(hosts, indices, max_result_window=max_window,
                       create_missing_indices=False)

def _init_statistics_web():
    charts = cfg(
        "web.yaml", "elasticsearch", "statistics", "charts", subpkg="web"
    )

    try:
        for chart in charts:
            chartdata_maker.add_chart(
                name=chart["chart_type"], rangetype=chart["time_range"]
            )
    except StatisticsError as e:
        raise StartupError(f"Failed initializing statistics chart data. {e}")

def init_web(cuckoo_cwd, loglevel, logfile=""):
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
    try:
        init_global_logging(loglevel, logfile)

        nodesinfos_path = Paths.nodeinfos_dump()
        if nodesinfos_path.is_file():
            settings_maker.set_nodesinfosdump_path(nodesinfos_path)

        load_configuration("web.yaml", subpkg="web")
        load_configuration("cuckoo.yaml", check_constraints=False)
        load_configuration("analysissettings.yaml")
        init_database()
        if cfg("web.yaml", "remote_storage", "enabled", subpkg="web"):
            _init_remote_storage()

        search = cfg(
            "web.yaml", "elasticsearch", "web_search", "enabled", subpkg="web"
        )
        stats = cfg(
            "web.yaml", "elasticsearch", "statistics", "enabled", subpkg="web"
        )
        if search or stats:
            _init_elasticsearch_web()

        if stats:
            _init_statistics_web()

        settings_maker.set_limits(cfg("analysissettings.yaml", "limits"))
        settings_maker.set_defaults(cfg("analysissettings.yaml", "default"))

    except StartupError as e:
        exit_error(f"Failed to initialize Cuckoo web. {e}")

    set_path_settings()

def start_web(host="127.0.0.1", port=8000, autoreload=False):
    args = ("cuckoo", "runserver", f"{host}:{port}")
    if not autoreload:
        args += ("--noreload",)

    execute_from_command_line(args)

def djangocommands(*args):
    execute_from_command_line(("cuckoo",) + args)

def init_and_get_wsgi():
    import logging
    from cuckoo.common.log import disable_console_colors
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
    init_web(cwd_path, loglevel)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cuckoo.web.web.settings')
    from django.core.wsgi import get_wsgi_application
    return get_wsgi_application()
