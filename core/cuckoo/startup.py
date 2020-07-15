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
from cuckoo.common.log import CuckooGlobalLogger, get_global_loglevel

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

    for subpkg, custom_loader in custom_load.items():
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
    rs = ResultServer(
        sockpath, cuckoocwd.root, ip, port, loglevel=get_global_loglevel()
    )
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

    taskrunner = TaskRunner(
        sockpath, cuckoocwd.root, loglevel=get_global_loglevel()
    )
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

def init_global_logging(level, filepath, use_logqueue=True, warningsonly=[]):
    import logging
    from cuckoo.common.log import (
        start_queue_listener, stop_queue_listener, set_level,
        add_rootlogger_handler, set_logger_level, logtime_fmt_str,
        file_handler, file_formatter, file_log_fmt_str, console_formatter,
        console_handler, console_log_fmt_str
    )

    # Set the Cuckoo log module level. This level will be set to
    # each handler added and logger created using the cuckoo log module.
    set_level(level)

    # Set the level of the giving logger names to warning. Is used to ignore
    # log messages lower than warning by third party libraries.
    for loggername in warningsonly:
        set_logger_level(loggername, logging.WARNING)

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
        # thread. These processes (resultserver, processing worker, etc) can
        # set use_logqueue=False
        add_rootlogger_handler(globallog_handler)

    consolelog_handler = console_handler()
    consolelog_handler.setLevel(level)
    consolelog_handler.setFormatter(
        console_formatter(console_log_fmt_str, logtime_fmt_str)
    )

    # Add extra handler to get logs to the console.
    # Let log to console printing be handled at by the actual caller.
    add_rootlogger_handler(consolelog_handler)

def add_machine(machinery_name, name, label, ip, platform, os_version="",
                mac_address=None, interface=None, snapshot=None, tags=[]):
    import cuckoo.machineries
    import shutil
    import tempfile
    from cuckoo.common.config import load_config, render_config, load_values

    conf_name = f"{machinery_name}.yaml"
    conf_path = Paths.config(conf_name, subpkg="machineries")
    if not os.path.exists(conf_path):
        raise StartupError(f"Configuration does not exist: {conf_path}")

    conf_templates = get_conftemplates(cuckoo.machineries)

    template_path = conf_templates.get(conf_name)
    if not template_path:
        raise StartupError(
            f"Cannot render configuration. No configuration "
            f"template for: {machinery_name}"
        )

    try:
        loaders = load_config(
            conf_path, subpkg="machineries", cache_config=False
        )
    except config.ConfigurationError as e:
        raise StartupError(
            f"Failed to load config file {conf_path}. {e}"
        )

    newmachine = {
        name: {
            "label": label,
            "ip": ip,
            "platform": platform,
            "os_version": os_version,
            "mac_address": mac_address,
            "snapshot": snapshot,
            "interface": interface,
            "tags": tags
        }
    }
    if name in loaders["machines"].value:
        raise StartupError(f"Machine {name} already exists in {conf_name}.")

    nested_loaders = loaders["machines"].make_typeloaders(newmachine)
    try:
        load_values(newmachine, nested_loaders)
    except config.ConfigurationError as e:
        raise StartupError(f"Configuration value error. {e}")

    loaders["machines"].value.update(nested_loaders)

    tmpdir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmpdir, conf_name)
    try:
        render_config(template_path, loaders, tmp_path)
        shutil.move(tmp_path, conf_path)
    finally:
        shutil.rmtree(tmpdir)
