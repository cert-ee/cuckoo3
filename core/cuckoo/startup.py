# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import time
from threading import Thread

from cuckoo.common import config, shutdown
from cuckoo.common.log import CuckooGlobalLogger, get_global_loglevel
from cuckoo.common.packages import get_conftemplates, enumerate_plugins
from cuckoo.common.startup import StartupError
from cuckoo.common.storage import Paths, cuckoocwd

log = CuckooGlobalLogger(__name__)

from . import started

"""All Cuckoo startup helper functions that start or prepare components 
must be declared here and register a stopping or cleanup method 
with shutdown.register_shutdown if anything has to be stopped 
on Cuckoo shutdown"""


def start_machinerymanager():
    from cuckoo.common.machines import read_machines_dump
    from cuckoo.machineries.abstracts import Machinery
    from .machinery import (
        MachineryManager, load_machineries, MachineryManagerError, shutdown_all
    )

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
    from cuckoo.common import task
    from .scheduler import task_queue, Scheduler

    pending = task.db_find_state(task.States.PENDING)

    if pending:
        task_queue.queue_many(pending)

    started.scheduler = Scheduler()
    shutdown.register_shutdown(started.scheduler.stop, order=2)

    started.scheduler.start()

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

def start_cuckoo(loglevel):
    from multiprocessing import set_start_method
    set_start_method("spawn")

    from cuckoo.common.config import MissingConfigurationFileError
    from cuckoo.common.startup import (
        init_elasticsearch, init_database, load_configurations,
        init_global_logging
    )

    # Initialize globing logging to cuckoo.log
    init_global_logging(loglevel, Paths.log("cuckoo.log"))

    log.info(f"Starting Cuckoo.", cwd=cuckoocwd.root)
    log.info("Loading configurations")
    try:
        load_configurations()
    except MissingConfigurationFileError as e:
        raise StartupError(f"Missing configuration file: {e}")

    init_elasticsearch(create_missing_indices=True)

    log.info("Starting resultserver")
    start_resultserver()
    log.info("Loading machineries and starting machinery manager")
    start_machinerymanager()
    log.info("Initializing database")
    init_database()
    log.info("Starting processing handler and workers")
    start_processing_handler()
    log.info("Starting task runner")
    start_taskrunner()
    log.info("Starting state controller")
    start_statecontroller()
    log.info("Starting scheduler")
    start_scheduler()
