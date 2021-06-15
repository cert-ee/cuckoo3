# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os

from .log import CuckooGlobalLogger
from .packages import (
    find_cuckoo_packages, get_conftemplates, get_conf_typeloaders
)
from .storage import Paths
from . import config, shutdown

log = CuckooGlobalLogger(__name__)

class StartupError(Exception):
    pass

def init_elasticsearch(hosts, indice_names, timeout=300,
                       max_result_window=10000,
                       create_missing_indices=False):

    from cuckoo.common.elastic import manager, ElasticSearchError

    manager.configure(
        hosts=hosts, analyses_index=indice_names["analyses"],
        tasks_index=indice_names["tasks"], events_index=indice_names["events"],
        timeout=timeout, max_result_window=max_result_window
    )
    try:
        manager.verify()
    except ElasticSearchError as e:
        raise StartupError(
            f"Failed during Elasticsearch connection check: {e}"
        )

    if not manager.all_indices_exist():
        if create_missing_indices:
            log.info("Creating missing Elasticsearch indices.")
            try:
                manager.create_missing_indices(Paths.elastic_templates())
            except ElasticSearchError as e:
                raise StartupError(
                    f"Failure during Elasticsearch index creation. {e}"
                )
        else:
            log.warning("One or more Elasticsearch indices missing")

def init_global_logging(level, filepath="", use_logqueue=True,
                        warningsonly=[]):
    import logging
    from .log import (
        start_queue_listener, stop_queue_listener, set_level,
        add_rootlogger_handler, set_logger_level, logtime_fmt_str,
        file_handler, file_formatter, file_log_fmt_str, console_formatter,
        console_handler, console_log_fmt_str, WARNINGSONLY, VERBOSE,
        enable_verbose
    )

    if not warningsonly:
        warningsonly = WARNINGSONLY

    # The custom VERBOSE level is only so we know when not to ignore
    # other modules than the Cuckoo ones. If it is set, any attempts to
    # increase logging levels higher than debug will be ignored.
    if level == VERBOSE:
        enable_verbose()
        level = logging.DEBUG

    # Set the Cuckoo log module level. This level will be set to
    # each handler added and logger created using the cuckoo log module.
    set_level(level)

    # Set the level of the giving logger names to warning. Is used to ignore
    # log messages lower than warning by third party libraries.
    for loggername in warningsonly:
        set_logger_level(loggername, logging.WARNING)

    if filepath:
        globallog_handler = file_handler(filepath, mode="a")
        globallog_handler.setFormatter(
            file_formatter(file_log_fmt_str, logtime_fmt_str)
        )

        if use_logqueue:
            # Ensure the log queue thread is stopped last when stopping Cuckoo
            shutdown.register_shutdown(stop_queue_listener, order=999)

            # Let file logging be handled by the queuelistener
            start_queue_listener(globallog_handler)
        else:
            # Low log line amount processes don't need a separate logwriting
            # thread. These processes (resultserver, processing worker, etc)
            # can set use_logqueue=False
            add_rootlogger_handler(globallog_handler)

    consolelog_handler = console_handler()
    consolelog_handler.setLevel(level)
    consolelog_handler.setFormatter(
        console_formatter(console_log_fmt_str, logtime_fmt_str)
    )

    # Add extra handler to get logs to the console.
    # Let log to console printing be handled at by the actual caller.
    add_rootlogger_handler(consolelog_handler)

def init_database():
    from cuckoo.common.db import dbms, CuckooDBDTable
    dbms.initialize(
        f"sqlite:///{Paths.dbfile()}", tablebaseclass=CuckooDBDTable
    )
    shutdown.register_shutdown(dbms.cleanup, order=998)


def init_safelist_db():
    from cuckoo.common.safelist import SafelistTable, safelistdb
    safelistdb.initialize(
        f"sqlite:///{Paths.safelist_db()}", tablebaseclass=SafelistTable
    )
    shutdown.register_shutdown(safelistdb.cleanup, order=999)

def create_configurations():
    """Create all configurations is the config folder of the cuckoocwd that
    has already been set."""
    for pkgname, subpkg, pkg in find_cuckoo_packages():
        conf_typeloaders, _ = get_conf_typeloaders(pkg)
        if not conf_typeloaders:
            continue

        templates = get_conftemplates(pkg)
        if not templates:
            continue

        for confname, typeloaders in conf_typeloaders.items():
            if subpkg:
                subpkg_confdir = Paths.config(subpkg=subpkg)
                if not os.path.isdir(subpkg_confdir):
                    os.mkdir(subpkg_confdir)

            config_path = Paths.config(file=confname, subpkg=subpkg)
            # Skip the creation of the configuration file if it already exists
            if os.path.isfile(config_path):
                # TODO implement configuration migration code.
                continue

            template_path = templates.get(confname)
            if not template_path:
                raise StartupError(
                    f"No configuration template exists for {confname}"
                )

            config.render_config(template_path, typeloaders, config_path)


def _load_machinery_configs():
    for machinery in config.cfg("cuckoo", "machineries"):
        confpath = Paths.config(file=f"{machinery}.yaml", subpkg="machineries")
        log.debug("Loading config.", confpath=confpath)
        try:
            config.load_config(confpath, subpkg="machineries")
        except config.ConfigurationError as e:
            raise StartupError(
                f"Failed to load config file {confpath}. {e}"
            )

def load_configurations():
    # Load cuckoo all configurations for Cuckoo and all installed Cuckoo
    # subpackages, except for subpackages listed in 'custom_load'.
    # These have custom loading routines.
    custom_load = {
        "machineries": _load_machinery_configs
    }
    for pkgname, subpkg, pkg in find_cuckoo_packages():
        if subpkg in custom_load:
            continue

        conf_typeloaders, exclude = get_conf_typeloaders(pkg)
        if not conf_typeloaders:
            continue

        for confname in conf_typeloaders:
            if confname in exclude:
                continue

            confpath = Paths.config(file=confname, subpkg=subpkg)
            if not os.path.isfile(confpath):
                raise config.MissingConfigurationFileError(
                    f"Configuration file {confname} is missing."
                )

            log.debug("Loading config.", confpath=confpath)
            try:
                config.load_config(confpath, subpkg=subpkg)
            except config.ConfigurationError as e:
                raise StartupError(
                    f"Failed to load config file {confpath}. {e}"
                )

    for subpkg, custom_loader in custom_load.items():
        custom_loader()
