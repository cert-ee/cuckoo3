# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import logging
import os
import threading
import time
from threading import Thread

from cuckoo.common import config, shutdown
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.startup import StartupError, MigrationNeededError
from cuckoo.common.storage import Paths, UnixSocketPaths, cuckoocwd

from .scheduler import NodesTracker

log = CuckooGlobalLogger(__name__)


"""All Cuckoo startup helper functions that start or prepare components 
must be declared here and register a stopping or cleanup method 
with shutdown.register_shutdown if anything has to be stopped 
on Cuckoo shutdown"""

class CuckooCtx:

    def __init__(self):
        self.nodes = NodesTracker(self)
        self.loglevel = logging.DEBUG
        self.scheduler = None
        self.state_controller = None
        self.processing_handler = None

def start_processing_handler(cuckooctx):
    from .runprocessing import ProcessingWorkerHandler
    cuckooctx.processing_handler = ProcessingWorkerHandler(cuckooctx)
    cuckooctx.processing_handler.daemon = True
    shutdown.register_shutdown(cuckooctx.processing_handler.stop)

    cuckooctx.processing_handler.set_worker_amount(
        identification=config.cfg(
            "cuckoo.yaml", "processing", "worker_amount", "identification"
        ),
        pre=config.cfg("cuckoo.yaml", "processing", "worker_amount", "pre"),
        post=config.cfg("cuckoo.yaml", "processing", "worker_amount", "post")
    )

    cuckooctx.processing_handler.start()

    while cuckooctx.processing_handler.do_run:
        if cuckooctx.processing_handler.setup_finished():
            break

        if cuckooctx.processing_handler.has_failed_workers():
            raise StartupError(
                "One or more processing workers failed to start"
            )

        time.sleep(1)

def start_statecontroller(cuckooctx):
    from .control import StateController
    sockpath = UnixSocketPaths.state_controller()
    if sockpath.exists():
        raise StartupError(
            f"Failed to start state controller: "
            f"Unix socket path already exists: {sockpath}"
        )

    cuckooctx.state_controller = StateController(sockpath, cuckooctx)
    shutdown.register_shutdown(cuckooctx.state_controller.stop)

    # Check if any untracked analyses exist after starting
    cuckooctx.state_controller.track_new_analyses()

    # Check if there are any analyses that have been exported and for
    # which their location has not been updated yet.
    cuckooctx.state_controller.set_remote()

    state_th = Thread(target=cuckooctx.state_controller.start)
    state_th.start()

def make_scheduler(cuckooctx, task_queue):
    from .scheduler import Scheduler
    sched = Scheduler(cuckooctx, task_queue)

    # Add scheduler to context for usage by other components
    cuckooctx.scheduler = sched

    # Ensure schedule stop is always called second (after stop message)
    shutdown.register_shutdown(sched.stop, order=2)

def import_vmcloak_vms(machinery_name, vms_path, machine_names=[]):
    from cuckoo.machineries.configtools import import_vmcloak_machines
    from cuckoo.machineries.errors import MachineryError

    if not os.path.isdir(vms_path):
        raise StartupError(f"'{vms_path}' is not a directory")

    if not os.listdir(vms_path):
        raise StartupError(f"'{vms_path}' is an empty directory")

    try:
        return import_vmcloak_machines(machinery_name, vms_path, machine_names)
    except MachineryError as e:
        raise StartupError(f"Import failed. {e}")

def delete_machines(machinery_name, machine_names):
    from cuckoo.machineries.configtools import delete_machines
    from cuckoo.machineries.errors import MachineryError
    try:
        return delete_machines(machinery_name, machine_names)
    except MachineryError as e:
        raise StartupError(f"Failure during deletion. {e}")

def add_machine(machinery_name, name, machine_dict):
    from cuckoo.machineries.configtools import add_machine
    from cuckoo.machineries.errors import MachineryError

    try:
        add_machine(machinery_name, name, machine_dict)
    except MachineryError as e:
        raise StartupError(f"Failed to add machine. {e}")


def start_importcontroller(cuckooctx):
    from .control import ImportController
    sockpath = Paths.unix_socket("importcontroller.sock")
    if os.path.exists(sockpath):
        raise StartupError(
            f"Failed to start import controller: "
            f"Unix socket path already exists: {sockpath}"
        )

    import_controller = ImportController(sockpath, cuckooctx)
    shutdown.register_shutdown(import_controller.stop)

    # Check if any untracked analyses exist after starting
    import_controller.import_importables()
    import_controller.start()

def start_importmode(loglevel):
    from multiprocessing import set_start_method
    set_start_method("spawn")

    from cuckoo.common.startup import (
        init_database, load_configurations, init_global_logging
    )

    ctx = CuckooCtx()
    ctx.loglevel = loglevel

    # Initialize globing logging to importmode.log
    init_global_logging(loglevel, Paths.log("importmode.log"))
    init_database()

    log.info("Starting import mode")
    log.info("Loading configurations")
    try:
        load_configurations()
    except config.MissingConfigurationFileError as e:
        raise StartupError(f"Missing configuration file: {e}")

    log.info("Starting import controller")
    start_importcontroller(ctx)

def start_localnode(cuckooctx):
    from cuckoo.node.startup import start_local

    from .nodeclient import LocalStreamReceiver, LocalNodeClient
    stream_receiver = LocalStreamReceiver()
    nodectx = start_local(stream_receiver, cuckooctx.loglevel)

    client = LocalNodeClient(cuckooctx, nodectx.node)
    stream_receiver.set_client(client)
    cuckooctx.nodes.add_node(client)

def start_resultretriever(cuckooctx, nodeapi_clients):
    from .retriever import ResultRetriever
    from multiprocessing import Process

    sockpath = UnixSocketPaths.result_retriever()
    if sockpath.exists():
        raise StartupError(
            f"Result retriever socket path already exists: {sockpath}"
        )

    retriever = ResultRetriever(
        sockpath, cuckoocwd, cuckooctx.loglevel
    )

    for client in nodeapi_clients:
        retriever.add_node(client.name, client)

    runner_proc = Process(target=retriever.start)

    def _retriever_stopper():
        runner_proc.terminate()
        runner_proc.join(timeout=30)

    shutdown.register_shutdown(_retriever_stopper)
    runner_proc.start()

    waited = 0
    MAXWAIT = 5
    while not sockpath.exists():
        if waited >= MAXWAIT:
            raise StartupError(
                f"Result retriever was not started after {MAXWAIT} seconds."
            )

        if not runner_proc.is_alive():
            raise StartupError("Result retriever stopped unexpectedly")
        waited += 0.5
        time.sleep(0.5)

def make_node_api_clients():
    from cuckoo.common.clients import NodeAPIClient, ClientError
    node_clients = []
    for name, values in config.cfg("distributed.yaml", "remote_nodes").items():
        client = NodeAPIClient(
            values["api_url"], values["api_key"], node_name=name
        )

        log.info("Loading remote node client", node=name, url=client.api_url)
        try:
            client.ping()
        except ClientError as e:
            raise StartupError(f"Error contacting remote node {name}. {e}")

        node_clients.append(client)

    return node_clients

def make_remote_node_clients(cuckooctx, node_api_clients):
    from cuckoo.common.clients import ClientError
    from cuckoo.node.node import NodeStates
    from .nodeclient import RemoteNodeClient, NodeClientLoop, NodeActionError
    import asyncio

    loop = asyncio.new_event_loop()
    wrapper = NodeClientLoop(loop)

    shutdown.register_shutdown(wrapper.stop)

    remotes_nodes = []
    for api in node_api_clients:
        remote_node = RemoteNodeClient(cuckooctx, api, wrapper)
        try:
            state = api.get_state()
            if state != NodeStates.WAITING_MAIN:
                log.warning(
                    "Remote node does not have expected state. Requesting "
                    "node to reset itself", node=api.name, state=state,
                    expected_state=NodeStates.WAITING_MAIN)
                api.reset()
        except ClientError as e:
            raise StartupError(
                f"Failure during node state retrieval or reset. {e}"
            )

        try:
            remote_node.init()
            loop.run_until_complete(remote_node.start_reader())
        except NodeActionError as e:
            raise StartupError(e)

        remotes_nodes.append(remote_node)
        cuckooctx.nodes.add_node(remote_node)

    return remotes_nodes, wrapper

def make_task_queue():
    from cuckoo.common.db import DatabaseMigrationNeeded
    from .taskqueue import TaskQueue

    try:
        return TaskQueue(Paths.queuedb())
    except DatabaseMigrationNeeded as e:
        raise MigrationNeededError(e, "Task queue database (taskqueuedb)")

def start_cuckoo_controller(loglevel, cancel_abandoned=False):
    from multiprocessing import set_start_method
    set_start_method("spawn")

    from cuckoo.common.startup import (
        init_database, load_configurations, init_global_logging
    )

    # Initialize globing logging to cuckoo.log
    init_global_logging(loglevel, Paths.log("cuckoo.log"))

    log.info("Starting Cuckoo controller", cwd=cuckoocwd.root)
    log.info("Loading configurations")
    try:
        load_configurations()
        config.load_config(Paths.config("distributed.yaml"))
    except config.MissingConfigurationFileError as e:
        raise StartupError(f"Missing configuration file: {e}")
    except config.ConfigurationError as e:
        raise StartupError(e)

    log.debug("Loading remote nodes")
    api_clients = make_node_api_clients()
    _init_elasticsearch_pre_startup()

    log.debug("Initializing database")
    init_database()

    cuckooctx = CuckooCtx()
    cuckooctx.loglevel = loglevel

    log.debug("Starting result retriever")
    start_resultretriever(cuckooctx, api_clients)

    log.debug("Initializing task queue")
    task_queue = make_task_queue()

    make_scheduler(cuckooctx, task_queue)

    remote_nodes, loop_wrapper = make_remote_node_clients(
        cuckooctx, api_clients
    )

    threading.Thread(target=loop_wrapper.start).start()

    log.debug("Starting processing handler and workers")
    start_processing_handler(cuckooctx)

    log.debug("Starting state controller")
    start_statecontroller(cuckooctx)

    log.debug("Starting scheduler")
    cuckooctx.scheduler.handle_abandoned(cancel=cancel_abandoned)
    cuckooctx.scheduler.start()

def _init_elasticsearch_pre_startup():
    # Elasticsearch initialization before starting processing workers.
    # This init is responsible for ensuring the indices will exist.

    if not config.cfg("elasticsearch.yaml", "enabled", subpkg="processing"):
        return

    from cuckoo.common.startup import init_elasticsearch

    hosts = config.cfg("elasticsearch.yaml", "hosts", subpkg="processing")
    indices = config.cfg(
        "elasticsearch.yaml", "indices", "names", subpkg="processing"
    )
    timeout = config.cfg("elasticsearch.yaml", "timeout", subpkg="processing")
    max_result = config.cfg(
        "elasticsearch.yaml", "max_result_window", subpkg="processing"
    )
    init_elasticsearch(
        hosts, indices, timeout=timeout, max_result_window=max_result,
        create_missing_indices=True
    )

def start_cuckoo(loglevel, cancel_abandoned=False):
    from multiprocessing import set_start_method
    set_start_method("spawn")

    from cuckoo.common.startup import (
        init_database, load_configurations, init_global_logging
    )

    # Initialize globing logging to cuckoo.log
    init_global_logging(loglevel, Paths.log("cuckoo.log"))

    log.info("Starting Cuckoo.", cwd=cuckoocwd.root)
    log.info("Loading configurations")
    try:
        load_configurations()
    except config.MissingConfigurationFileError as e:
        raise StartupError(f"Missing configuration file: {e}")
    except config.ConfigurationError as e:
        raise StartupError(e)

    _init_elasticsearch_pre_startup()

    log.debug("Initializing database")
    init_database()

    log.debug("Initializing task queue")
    task_queue = make_task_queue()
    cuckooctx = CuckooCtx()
    cuckooctx.loglevel = loglevel
    make_scheduler(cuckooctx, task_queue)

    log.debug("Starting local task node")
    start_localnode(cuckooctx)

    log.debug("Starting processing handler and workers")
    start_processing_handler(cuckooctx)

    log.debug("Starting state controller")
    start_statecontroller(cuckooctx)

    log.debug("Starting scheduler")
    cuckooctx.scheduler.handle_abandoned(cancel=cancel_abandoned)
    cuckooctx.scheduler.start()
