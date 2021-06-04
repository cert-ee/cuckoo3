# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.
import logging
import os
import threading
import time
from threading import Thread

from cuckoo.common import config, shutdown
from cuckoo.common.log import CuckooGlobalLogger, get_global_loglevel
from cuckoo.common.packages import get_conftemplates
from cuckoo.common.startup import StartupError
from cuckoo.common.storage import Paths, UnixSocketPaths, cuckoocwd

from .scheduler import NodesTracker

log = CuckooGlobalLogger(__name__)


"""All Cuckoo startup helper functions that start or prepare components 
must be declared here and register a stopping or cleanup method 
with shutdown.register_shutdown if anything has to be stopped 
on Cuckoo shutdown"""

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

        time.sleep(1)

    if cuckooctx.processing_handler.has_failed_workers():
        raise StartupError("One or more processing workers failed to start")

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

def start_importcontroller():
    from .control import ImportController
    sockpath = Paths.unix_socket("importcontroller.sock")
    if os.path.exists(sockpath):
        raise StartupError(
            f"Failed to start import controller: "
            f"Unix socket path already exists: {sockpath}"
        )

    import_controller = ImportController(sockpath)
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
    start_importcontroller()

def start_localnode(cuckooctx):
    from cuckoo.node.startup import start_local

    from .nodeclient import LocalStreamReceiver, LocalNodeClient
    stream_receiver = LocalStreamReceiver()
    nodectx = start_local(stream_receiver)

    client = LocalNodeClient(cuckooctx, nodectx.node)
    stream_receiver.set_client(client)
    cuckooctx.nodes.add_node(client)

def start_resultretriever(nodeapi_clients):
    from .retriever import ResultRetriever
    from multiprocessing import Process

    sockpath = UnixSocketPaths.result_retriever()
    if sockpath.exists():
        raise StartupError(
            f"Result retriever socket path already exists: {sockpath}"
        )

    retriever = ResultRetriever(
        sockpath, cuckoocwd, get_global_loglevel()
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

        log.debug("Loading remote node client", node=name, url=client.api_url)
        try:
            client.ping()
        except ClientError as e:
            raise StartupError(f"Error contacting remote node {name}. {e}")

        node_clients.append(client)

    return node_clients

def make_remote_node_clients(cuckooctx, node_api_clients):
    from .nodeclient import RemoteNodeClient, NodeClientLoop, NodeActionError
    import asyncio

    loop = asyncio.new_event_loop()
    wrapper = NodeClientLoop(loop)

    shutdown.register_shutdown(wrapper.stop)

    remotes_nodes = []
    for api in node_api_clients:
        remote_node = RemoteNodeClient(cuckooctx, api, wrapper)
        try:
            remote_node.init()
            loop.run_until_complete(remote_node.start_reader())
        except NodeActionError as e:
            raise StartupError(e)

        remotes_nodes.append(remote_node)
        cuckooctx.nodes.add_node(remote_node)

    return remotes_nodes, wrapper

class CuckooCtx:

    def __init__(self):
        self.nodes = NodesTracker(self)
        self.scheduler = None
        self.state_controller = None
        self.processing_handler = None

def start_cuckoo_controller(loglevel):
    from multiprocessing import set_start_method
    set_start_method("spawn")

    from cuckoo.common.startup import (
        init_database, load_configurations, init_global_logging
    )
    from cuckoo.common.log import set_logger_level
    from .taskqueue import TaskQueue

    # Initialize globing logging to cuckoo.log
    init_global_logging(loglevel, Paths.log("cuckoo.log"))

    set_logger_level("urllib3.connectionpool", logging.ERROR)

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

    log.debug("Starting result retriever")
    start_resultretriever(api_clients)

    log.debug("Initializing task queue")
    task_queue = TaskQueue(Paths.queuedb())
    cuckooctx = CuckooCtx()
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

def start_cuckoo(loglevel):
    try:
        from multiprocessing import set_start_method
        set_start_method("spawn")

        from cuckoo.common.startup import (
            init_database, load_configurations, init_global_logging
        )
        from .taskqueue import TaskQueue

        # Initialize globing logging to cuckoo.log
        init_global_logging(loglevel, Paths.log("cuckoo.log"))

        log.info("Starting Cuckoo.", cwd=cuckoocwd.root)
        log.info("Loading configurations")
        try:
            load_configurations()
        except config.MissingConfigurationFileError as e:
            raise StartupError(f"Missing configuration file: {e}")

        _init_elasticsearch_pre_startup()

        log.debug("Initializing database")
        init_database()

        log.debug("Initializing task queue")
        task_queue = TaskQueue(Paths.queuedb())
        cuckooctx = CuckooCtx()
        make_scheduler(cuckooctx, task_queue)

        log.debug("Starting local task node")
        start_localnode(cuckooctx)

        log.debug("Starting processing handler and workers")
        start_processing_handler(cuckooctx)

        log.debug("Starting state controller")
        start_statecontroller(cuckooctx)

        log.debug("Starting scheduler")
        cuckooctx.scheduler.start()
    except Exception as e:
        log.exception("failed", error=e)
        raise StartupError(e)
