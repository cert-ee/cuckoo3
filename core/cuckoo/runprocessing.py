# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import logging
import multiprocessing
import os
import select
import threading
import traceback

from cuckoo.common.config import MissingConfigurationFileError
from cuckoo.common.ipc import (
    UnixSocketServer, UnixSockClient, ReaderWriter, NotConnectedError
)
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.packages import enumerate_plugins
from cuckoo.common.startup import (
    init_global_logging, load_configurations, StartupError
)
from cuckoo.common.storage import Paths, cuckoocwd
from cuckoo.common import shutdown
from cuckoo.processing import abtracts
from cuckoo.processing.errors import PluginError
from cuckoo.processing.worker import (
    PreProcessingRunner, AnalysisContext, TaskContext, PostProcessingRunner
)

log = CuckooGlobalLogger(__name__)

class PluginWorkerError(Exception):
    pass

class States(object):
    SETUP = "setup"
    READY = "ready"
    IDLE = "idle"
    STOPPED = "stopped"
    WORKING = "working"
    FINISHED = "finished"
    WORK_FAIL = "work_failed"
    WORKER_FAIL = "worker_failed"
    SETUP_FAIL = "setup_failed"


class WorkReceiver(UnixSocketServer):

    PLUGIN_BASEPATH = "cuckoo.processing"
    REPORTING_PLUGIN_PATH = f"{PLUGIN_BASEPATH}.reporting"

    PLUGINS = {
        "identification": {
            "processing": (
                f"{PLUGIN_BASEPATH}.identification", abtracts.Processor
            ),
            "reporting": (REPORTING_PLUGIN_PATH, abtracts.Reporter)
        },
        "pre": {
            "processing": (f"{PLUGIN_BASEPATH}.pre", abtracts.Processor),
            "reporting": (REPORTING_PLUGIN_PATH, abtracts.Reporter)
        },
        "post": {
            "eventconsuming": (
                f"{PLUGIN_BASEPATH}.post.eventconsumer", abtracts.EventConsumer
            ),
            "processing": (f"{PLUGIN_BASEPATH}.post", abtracts.Processor),
            "reporting": (REPORTING_PLUGIN_PATH, abtracts.Reporter)
        }
    }

    def __init__(self, sockpath, worktype, name, cuckoocwd,
                 loglevel=logging.DEBUG):
        self.name = name
        self.worktype = worktype
        self.cuckoocwd = cuckoocwd
        self.loglevel = loglevel

        self.reader = None
        self.work_plugins = []
        self.reporting_plugins = []
        self.state = ""

        self.plugin_classes = {}

        super().__init__(sockpath)

    def start(self):
        def _stop_wrapper():
            if self.do_run:
                log.info(
                    "Worker stopping..", worker=self.name,
                    worktype=self.worktype
                )
                self.stop()
                self.cleanup()

        shutdown.register_shutdown(_stop_wrapper)

        cuckoocwd.set(
            self.cuckoocwd.root, analyses_dir=self.cuckoocwd.analyses
        )
        init_global_logging(
            self.loglevel, Paths.log("cuckoo.log"), use_logqueue=False
        )

        log.debug("Loading configuration files", worker=self.name)
        try:
            load_configurations()
        except MissingConfigurationFileError as e:
            log.fatal_error(
                "Missing configuration file.", error=e, includetrace=False
            )

        try:
            self.initialize_workrunners()
        except StartupError as e:
            log.fatal_error(
                "Error during work runner initialization",
                worker=self.name, error=e, includetrace=False
            )

        self.create_socket(backlog=1)
        self.start_accepting()

    def send_msg(self, message_dict):
        self.reader.send_json_message(message_dict)

    def initialize_workrunners(self):
        PreProcessingRunner.init_once()
        PostProcessingRunner.init_once()

    def initialize_plugins(self):
        plugins = self.PLUGINS.get(self.worktype)

        for plugintype, path_abstract in plugins.items():
            # Import plugins for the stage from path set in PLUGINS. The value
            # for each key in a stage must be a
            # tuple(path.to.import, Abstract class of classes to import)

            path, abstract = path_abstract
            try:
                plugin_classes = enumerate_plugins(path, globals(), abstract)
            except ImportError as e:
                log.error(
                    "Failed to import plugins for worker", worker=self.name,
                    importpath=path, abstractclass=abstract, error=e
                )
                return False

            usable_classes = []
            for plugin_class in plugin_classes:
                try:
                    if plugin_class.enabled():
                        plugin_class.init_once()
                except PluginError as e:
                    log.error(
                        "Failed to initialize plugin class",
                        plugin_class=plugin_class,
                        worker=self.name, error=e
                    )
                    return False
                except Exception as e:
                    log.exception(
                        "Failed to initialize plugin class",
                        plugin_class=plugin_class, error=e, worker=self.name
                    )
                    return False

                usable_classes.append(plugin_class)

            stage_classes = self.plugin_classes.setdefault(self.worktype, {})
            plugintype_classes = stage_classes.setdefault(plugintype, [])
            plugintype_classes.extend(usable_classes)

        return True

    def update_state(self, state, info={}):
        msg = {}
        msg.update(info)
        msg["state"] = state
        self.send_msg(msg)
        self.state = state

    def handle_connection(self, sock, addr):
        reader = ReaderWriter(sock)
        self.reader = reader
        self.track(sock, reader)

        if self.initialize_plugins():
            self.update_state(States.READY)
        else:
            self.update_state(States.SETUP_FAIL)

    def _make_task_processor(self, analysis_id, task_id):
        taskctx = TaskContext(analysis_id, task_id)

        event_consumers = self.plugin_classes[self.worktype]["eventconsuming"]
        processing_classes = self.plugin_classes[self.worktype]["processing"]
        reporting_classes = self.plugin_classes[self.worktype]["reporting"]
        runner = PostProcessingRunner(
            taskctx, event_consumer_classes=event_consumers,
            processing_classes=processing_classes,
            reporting_classes=reporting_classes
        )
        return taskctx, runner

    def _make_analysis_processor(self, analysis_id):
        analysisctx = AnalysisContext(self.worktype, analysis_id)

        processing_classes = self.plugin_classes[self.worktype]["processing"]
        reporting_classes = self.plugin_classes[self.worktype]["reporting"]
        runner = PreProcessingRunner(
            analysisctx, processing_classes=processing_classes,
            reporting_classes=reporting_classes
         )
        return analysisctx, runner

    def handle_message(self, sock, m):
        try:
            if "analysis_id" in m:
                if "task_id" in m:
                    processing_ctx, runner = self._make_task_processor(
                        m["analysis_id"], m["task_id"]
                    )
                else:
                    processing_ctx, runner = self._make_analysis_processor(
                        m["analysis_id"]
                    )
            else:
                self.send_msg(
                    {"error": "Missing key 'analysis_id' or 'task_id'"}
                )
                self.untrack(sock)
                return
        except (ValueError, FileNotFoundError, KeyError) as e:
            log.error(
                "Error while creating processing context",
                worker=self.name, error=e
            )
            self.update_state(States.WORK_FAIL)
            return

        try:
            processing_ctx.log.info(
                "Starting work", worker=self.name, worktype=self.worktype
            )
            runner.start()

            if processing_ctx.completed:
                self.update_state(States.FINISHED)
            else:
                self.update_state(States.WORK_FAIL)
        except Exception as e:
            log.exception("Worker fail", worker=self.name, error=e)
            self.update_state(
                States.WORKER_FAIL, {
                    "traceback": traceback.format_exc(),
                    "error": str(e)
                }
            )
        finally:
            processing_ctx.close()
            del runner
            del processing_ctx

class _ProcessingJob:

    def __init__(self, worktype, analysis_id, task_id=None):
        self.worktype = worktype
        self.analysis_id = analysis_id
        self.task_id = task_id

    def __repr__(self):
        s = f"<Worktype={self.worktype}, analysis_id={self.analysis_id}"
        if self.task_id:
            s += f", task_id={self.task_id}"
        return s + ">"

    def to_dict(self):
        d = {
            "analysis_id": self.analysis_id,
            "worktype": self.worktype,
        }

        if self.task_id:
            d.update({
                "task_id": self.task_id
            })

        return d

class ProcessingWorkerHandler(threading.Thread):

    def __init__(self, cuckooctx):
        super().__init__()
        self.ctx = cuckooctx
        self.do_run = True
        self.unready_workers = []
        self.connected_workers = {}

        # Queues with work
        self.queues = {
            "identification": [],
            "pre": [],
            "post": []
        }

        self._workers_started = False
        self._workers_fail = False

        self._max_workers = {
            "identification": 1,
            "pre": 1,
            "post": 1
        }

    def identify(self, analysis_id):
        self.queues["identification"].append(_ProcessingJob(
            "identification", analysis_id
        ))

    def pre_analysis(self, analysis_id):
        self.queues["pre"].append(_ProcessingJob(
            "pre", analysis_id
        ))

    def post_analysis(self, analysis_id, task_id):
        self.queues["post"].append(_ProcessingJob(
            "post", analysis_id, task_id
        ))

    def set_worker_amount(self, identification=1, pre=1, post=1):
        self._max_workers = {
            "identification": identification,
            "pre": pre,
            "post": post
        }

    def run(self):
        log.debug("Starting processing workers")
        for worktype, max_workers in self._max_workers.items():
            for worker_number in range(max_workers):
                self.start_worker(f"{worktype}{worker_number}", worktype)

        self._workers_started = True
        self.handle_workers()

    def find_worker(self, name):
        for worker in self.connected_workers.values():
            if worker["name"] == name:
                return worker

        return None

    def stop(self):
        self.do_run = False

        # If any workers have not stopped yet, stop them. Make a list of
        # generator so we can delete from workers dict while iterating.
        workers = list(self.connected_workers.values()) + self.unready_workers
        for worker in workers:
            try:
                self.stop_worker(worker)
            except OSError:
                pass

    def setup_finished(self):
        if not self._workers_started:
            return False

        workers = list(self.connected_workers.values()) + self.unready_workers
        for worker in workers:
            if not worker["state"] or worker["state"] == States.SETUP:
                return False

        return True

    def has_failed_workers(self):
        for worker in self.unready_workers:
            if not worker["process"].is_alive():
                return True

        for worker in self.connected_workers.values():
            if not worker["process"].is_alive():
                return True

        return self._workers_fail

    def start_worker(self, name, worktype):
        if name in self.connected_workers:
            raise KeyError(f"Processing worker {name} already exists")

        sockpath = Paths.unix_socket(f"{name}.sock")
        if os.path.exists(sockpath):
            # TODO use pidfile to determine if a sockpath can be removed
            log.warning(
                "Unix socket path still exists. Removing it.",
                sockpath=sockpath
            )
            os.unlink(sockpath)

        log.info(f"Starting {worktype} worker.", workername=name)
        worker = WorkReceiver(
            sockpath, worktype, name, cuckoocwd,
            loglevel=self.ctx.loglevel
        )
        proc = multiprocessing.Process(target=worker.start)
        proc.daemon = True
        proc.name = name
        proc.start()
        log.debug("Worker process started", workername=name, pid=proc.pid)

        self.unready_workers.append({
            "name": name,
            "worktype": worktype,
            "process": proc,
            "comm": UnixSockClient(sockpath),
            "sockpath": sockpath,
            "state": None,
            "job": None
        })

    def requeue_work(self, worker):
        if worker["state"] != States.WORKING:
            log.error(
                "Cannot requeue work for worker without work", worker=worker
            )
            return

        job = worker["job"]
        worktype = worker["worktype"]
        log.warning(
            "Requeuing job from worker", workername=worker["name"], job=job,
            worktype=worktype
        )
        self.queues[worktype].insert(0, job)

    def stop_worker(self, worker):
        log.debug("Stopping worker", workername=worker["name"])
        try:
            worker["process"].terminate()
        except OSError:
            pass

        self.set_worker_state(States.STOPPED, worker)

    def untrack_worker(self, worker):
        if worker["state"] != States.STOPPED:
            raise NotImplementedError(
                f"Cannot untrack a worker without stopping it first. {worker}"
            )

        self.connected_workers.pop(worker["comm"].sock, None)
        worker["comm"].cleanup()

    def set_worker_state(self, state, worker):
        worker["state"] = state

    def setup_comm(self, worker):
        sockpath = worker["sockpath"]

        # While the .connect method of the client also verifies if the sockpath
        # exists, it also waits until it does. We don't want to wait for it
        # to exist here.
        if not os.path.exists(sockpath):
            return False

        comm = worker["comm"]
        comm.connect()

        return True

    def handle_incoming(self, sock):
        """Handle incoming finishes, fail, ready messages"""
        # Retrieve the worker information that is mapped to the connected sock
        worker = self.connected_workers[sock]

        try:
            msg = worker["comm"].recv_json_message()
        except (EOFError, ValueError) as e:
            # If worker is working or setting up, we expect a message. Messages
            # during other states can be ignored.
            log.error(
                "Invalid message received from worker",
                workername=worker["name"], error=e
            )

            if worker["state"] in (States.WORKING, States.SETUP):
                self.requeue_work(worker)
                self.stop_worker(worker)
            return

        except NotConnectedError:
            if not self.do_run:
                return

            log.error(
                "Worker disconnected unexpectedly", workername=worker["name"]
            )
            self.stop_worker(worker)

            # Untrack as it is disconnected
            self.untrack_worker(worker)
            return

        # Read the state send to us by the worker
        state = msg["state"]

        # Worker finished its current job and is ready for another.
        if state == States.FINISHED:
            self.controller_workdone(worker)

            job = worker["job"]
            worker["job"] = None
            self.set_worker_state(States.IDLE, worker)
            log.debug(
                "Worker finished job", workername=worker["name"], job=job
            )

        # Worker has set up/loaded plugins and is ready to receive a job.
        elif state == States.READY:
            log.debug("Worker is done setting up.", workername=worker["name"])
            self.set_worker_state(States.IDLE, worker)

        # The job of the worker failed. Inform the state controller of the
        # fail
        elif state == States.WORK_FAIL:
            self.controller_workfail(worker)
            worker["job"] = None
            self.set_worker_state(States.IDLE, worker)

        # A unhandled exception occurred and processing and/or reporting was
        # likely abruptly stopped. Inform the controller and perform any
        # handling of the failing worker.
        elif state == States.WORKER_FAIL:
            self._workers_fail = True
            self.controller_workfail(worker)
            # TODO: Depending on what the fail is, we might want to kill and
            # restart the worker?
            log.error(
                "Unhandled exception in worker", workername=worker["name"],
                error=msg.get("error", ""), traceback=msg.get("traceback", "")
            )

        elif state == States.SETUP_FAIL:
            self._workers_fail = True
            self.set_worker_state(States.SETUP_FAIL, worker)
            self.stop_worker(worker)
            log.error(
                "Worker setup failed. See worker logs",
                workername=worker["name"]
            )

    def controller_workdone(self, worker):
        self.ctx.state_controller.work_done(
            worktype=worker["worktype"],
            analysis_id=worker["job"].analysis_id,
            task_id=worker["job"].task_id
        )

    def controller_workfail(self, worker):
        self.ctx.state_controller.work_failed(
            worktype=worker["worktype"],
            analysis_id=worker["job"].analysis_id,
            task_id=worker["job"].task_id
        )

    def available_workers(self):
        available = []
        for worker in self.connected_workers.values():
            if worker["state"] == States.IDLE:
                available.append(worker)

        return available

    def assign_work(self, workers):
        for worker in workers:
            queue = self.queues[worker["worktype"]]
            if not queue:
                continue

            processing_job = queue.pop(0)
            self.assign_worker(worker, processing_job)

    def assign_worker(self, worker, job):
        log.debug(
            "Assigning job to worker", workername=worker["name"],
            job=job
        )

        worker["comm"].send_json_message(job.to_dict())

        worker["job"] = job
        self.set_worker_state(States.WORKING, worker)

    def handle_workers(self):
        while self.do_run:
            for worker in self.unready_workers[:]:
                if self.setup_comm(worker):
                    # Move the current worker to the connected workers
                    self.connected_workers[worker["comm"].sock] = worker
                    self.set_worker_state(States.SETUP, worker)
                    self.unready_workers.remove(worker)

            incoming, _o, _ = select.select(
                self.connected_workers.keys(), [], [], 1
            )
            for sock in incoming:
                self.handle_incoming(sock)

            available = self.available_workers()
            if available:
                self.assign_work(available)
