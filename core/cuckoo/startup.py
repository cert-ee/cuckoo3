# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import time
from importlib import import_module
from pkgutil import iter_modules
from threading import Thread

from cuckoo.common import config
from cuckoo.common.packages import (
    get_conf_typeloaders, get_conftemplates, enumerate_plugins
)
from cuckoo.common.storage import Paths, cuckoocwd
from cuckoo.common.log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

from . import started, shutdown

"""All Cuckoo startup helper functions that start or prepare components 
must be declared here and register a stoping or cleanup method 
with shutdown.register_shutdown if anything has to be stopped 
on Cuckoo shutdown"""

class StartupError(Exception):
    pass

def find_cuckoo_packages(do_import=True):
    """Returns a list of tuples containing the full package name,
    a subpackage name, and imported module (optional) of all
     packages part of the cuckoo namespace"""
    import cuckoo
    found = [("cuckoo", "", cuckoo)]

    module_iter = iter_modules(cuckoo.__path__)
    for _, name, is_package in module_iter:
        if is_package:
            fullname = f"cuckoo.{name}"
            if not do_import:
                found.append((fullname, name, None))
            else:
                found.append((fullname, name, import_module(fullname)))

    return found

def load_machinery_configs():
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
        "machineries": load_machinery_configs
    }
    for pkgname, subpkg, pkg in find_cuckoo_packages(do_import=True):
        if subpkg in custom_load:
            continue

        conf_typeloaders = get_conf_typeloaders(pkg)
        if not conf_typeloaders:
            continue

        for confname in conf_typeloaders:
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

    for custom_loader in custom_load.values():
        custom_loader()


def create_configurations():
    """Create all configurations is the config folder of the cuckoocwd that
    has already been set."""
    for pkgname, subpkg, pkg in find_cuckoo_packages(do_import=True):
        conf_typeloaders = get_conf_typeloaders(pkg)
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

def start_machinerymanager():
    from .machinery import (
        MachineryManager, load_machineries, read_machines_dump,
        MachineryManagerError, shutdown_all
    )
    from cuckoo.machineries.abstracts import Machinery

    all_machineries = enumerate_plugins(
        "cuckoo.machineries.modules", globals(), Machinery
    )
    enabled = config.cfg("cuckoo", "machineries")

    machinery_classes = []
    for machinery_class in all_machineries:
        if not machinery_class.name:
            continue

        if machinery_class.name.lower() in enabled:
            machinery_classes.append(machinery_class)

    # Load the machine states file if it is present.
    machine_states = {}
    dump_path = Paths.machinestates()
    if os.path.isfile(dump_path):
        machine_states = read_machines_dump(dump_path)

    try:
        load_machineries(machinery_classes, machine_states=machine_states)
    except MachineryManagerError as e:
        raise StartupError(f"Machinery loading failure: {e}")

    # Register the machinery stopping method as one that must be called last
    # to ensure any machines started during shutdown is still stopped.
    shutdown.register_shutdown(shutdown_all, order=999)

    sockpath = Paths.unix_socket("machinerymanager.sock")
    if os.path.exists(sockpath):
        raise StartupError(
            f"Machinery manager socket path already exists: {sockpath}"
        )

    manager = MachineryManager(sockpath)
    started.machinery_manager = manager

    shutdown.register_shutdown(manager.stop)

    manager_th = Thread(target=manager.start)
    manager_th.start()

def init_database():
    from .db import dbms
    dbms.initialize(Paths.dbfile())
    shutdown.register_shutdown(dbms.cleanup, order=998)

def start_processing_handler():
    from .runprocessing import ProcessingWorkerHandler
    started.processing_handler = ProcessingWorkerHandler()
    shutdown.register_shutdown(started.processing_handler.stop)
    started.processing_handler.start()

def start_statecontroller():
    from .control import StateController
    sockpath = Paths.unix_socket("statecontroller.sock")
    if os.path.exists(sockpath):
        raise StartupError(
            f"Failed to start state controller: "
            f"Unix socket path already exists: {sockpath}"
        )

    started.state_controller = StateController(sockpath)
    shutdown.register_shutdown(started.state_controller.stop)

    # Check if any untracked analyses exist after starting
    started.state_controller.track_new_analyses()

    state_th = Thread(target=started.state_controller.start)
    state_th.start()

def start_resultserver():
    from .resultserver import ResultServer, servers
    from multiprocessing import Process

    sockpath = Paths.unix_socket("resultserver.sock")
    if os.path.exists(sockpath):
        raise StartupError(
            "Resultserver unix socket already/still exists. "
            "Remove it there is no other Cuckoo instance running"
            f" using the specified Cuckoo CWD. {sockpath}"
        )

    ip = config.cfg("cuckoo", "resultserver", "listen_ip")
    port = config.cfg("cuckoo", "resultserver", "listen_port")
    rs = ResultServer(sockpath, cuckoocwd.root, ip, port)
    log.debug(
        "Starting resultserver.", listenip=ip, listenport=port,
        sockpath=sockpath, cwd=cuckoocwd.root
    )
    rs_proc = Process(target=rs.start)

    def _rs_stopper():
        rs_proc.terminate()

    shutdown.register_shutdown(_rs_stopper)
    rs_proc.start()

    waited = 0
    MAXWAIT = 5
    while not os.path.exists(sockpath):
        if waited >= MAXWAIT:
            raise StartupError(
                f"Resultserver was not started after {MAXWAIT} seconds."
            )

        if not rs_proc.is_alive():
            raise StartupError("Resultserver stopped unexpectedly")
        waited += 0.5
        time.sleep(0.5)

    log.debug("Resultserver process started.", pid=rs_proc.pid)

    servers.add(sockpath, ip, port)

def start_taskrunner():
    from .taskrunner import TaskRunner
    from multiprocessing import Process

    sockpath = Paths.unix_socket("taskrunner.sock")
    if os.path.exists(sockpath):
        raise StartupError(
            f"Task runner socket path already exists: {sockpath}"
        )

    taskrunner = TaskRunner(sockpath, cuckoocwd.root)
    runner_proc = Process(target=taskrunner.start)

    def _taskrunner_stopper():
        runner_proc.terminate()
        runner_proc.join(timeout=30)

    # This should be stopped as one of the first components. This way, tasks
    # that are stopped during a run can still more cleanly stop.
    shutdown.register_shutdown(_taskrunner_stopper, order=2)
    runner_proc.start()

    waited = 0
    MAXWAIT = 5
    while not os.path.exists(sockpath):
        if waited >= MAXWAIT:
            raise StartupError(
                f"Task runner was not started after {MAXWAIT} seconds."
            )

        if not runner_proc.is_alive():
            raise StartupError("Task runner stopped unexpectedly")
        waited += 0.5
        time.sleep(0.5)

def start_scheduler():
    from .scheduler import task_queue, Scheduler
    from .db import dbms, Task, TaskStates

    ses = dbms.session()
    try:
        pending = ses.query(Task).filter_by(state=TaskStates.PENDING)
    finally:
        ses.close()

    if pending:
        task_queue.queue_many(pending)

    started.scheduler = Scheduler()
    shutdown.register_shutdown(started.scheduler.stop, order=2)

    started.scheduler.start()

def init_global_logging(level, filepath):
    from logging import StreamHandler
    import logging
    from logging.handlers import WatchedFileHandler
    from cuckoo.common.log import (
        start_queue_listener, stop_queue_listener, KeyValueLogFormatter,
        ConsoleFormatter, set_level, add_rootlogger_handler, ColorText
    )

    # Replace WARNING with WARN to keep log line shorter,
    # alligned, and readable
    logging.addLevelName(logging.WARNING, "WARN")

    # Set the Cuckoo log module level. This level will be set to
    # each handler added and logger created using the cuckoo log module.
    set_level(level)

    file_log_fmt = "%(asctime)s %(levelname)-5s [%(name)s]: %(message)s"
    logtime_fmt = "%Y-%m-%d %H:%M:%S"
    globallog_h = WatchedFileHandler(filepath, mode="a")
    globallog_h.setFormatter(KeyValueLogFormatter(file_log_fmt, logtime_fmt))

    # Ensure the log queue thread is stopped last when stopping Cuckoo
    shutdown.register_shutdown(stop_queue_listener, order=999)

    # Let file logging be handled by the queuelistener
    start_queue_listener(globallog_h)

    # The console formatter has a '-22' because the console formatter
    # adds ansi colors, which adds length to the levelname. If the current
    # terminal does not support colors, use -5.
    format_len = -22
    if not ColorText.terminal_supported():
        format_len = -5

    console_fmt = f"%(asctime)s %(levelname){format_len}s " \
                  f"[%(name)s]: %(message)s"
    streamhandler = StreamHandler()
    streamhandler.setLevel(logging.DEBUG)
    streamhandler.setFormatter(ConsoleFormatter(console_fmt, logtime_fmt))

    # Add extra handler to get logs to the console.
    # Let log to console printing be handled at by the actual caller.
    add_rootlogger_handler(streamhandler)
