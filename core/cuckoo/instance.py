# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import multiprocessing
import os
import select
import signal
import traceback

from cuckoo.processing import helpers, typehelpers

from .ipc import UnixSocketServer, UnixSockClient, ReaderWriter
from .storage import Paths, AnalysisPaths

class PluginWorkerError(Exception):
    pass

class States(object):
    SETUP = "setup"
    READY = "ready"
    IDLE = "idle"
    WORKING = "working"
    FINISHED = "finished"
    WORK_FAIL = "work_failed"
    WORKER_FAIL = "worker_failed"
    SETUP_FAIL = "setup_failed"

class PluginWorker(object):

    def __init__(self, worktype, analysis_id, analysis_path, work_plugins,
                 reporting_plugins, taskid=None, binary_path=None):
        self.worktype = worktype
        self.analysis_id = analysis_id
        self.analysis_path = analysis_path
        self.work_plugins = work_plugins
        self.reporting_plugins = reporting_plugins
        self.taskid = taskid
        self.binary_path = binary_path

        self.errtracker = helpers.ErrorTracker()

    def get_plugin_instances(self, classes):
        # TODO: add configurations and only load enabled plugins
        # The plugin system should probably have its own structure from
        # which we can generate configuration files. This ends the requirement
        # for Cuckoo core to ship *all* config templates.
        # TODO the ability to not run or run a module depending on the target
        # category.

        analysis_info = typehelpers.Analysis.from_file(
            os.path.join(self.analysis_path, "analysis.json")
        )

        identification = {}
        ident_path = os.path.join(self.analysis_path, "identification.json")
        if os.path.exists(ident_path):
            identification = typehelpers.Identification.from_file(ident_path)

        instances = []
        for plugin_class in classes:
            try:
                instance = plugin_class(
                    analysis=analysis_info, analysis_path=self.analysis_path,
                    identification=identification, task_id=self.taskid,
                    submitted_file=self.binary_path
                )
                instance.init()
            except Exception as e:
                print(
                    f"ERROR: Failed to initialize plugin: {plugin_class}. "
                    f"Error: {e}"
                )
                continue

            instances.append(instance)

        instances.sort(key=lambda plugin: plugin.ORDER)
        return instances

    def start(self):
        instances = self.get_plugin_instances(self.work_plugins)
        results = self.run_work_plugins(instances)

        if self.errtracker.errors:
            print(
                f"{len(self.errtracker.errors)} error(s) during "
                f"{self.analysis_id} {self.worktype} work"
            )

        self.run_reporting_plugins(self.reporting_plugins, results)

    def run_work_plugins(self, instances):
        results = {}

        # Run all plugin instances.
        for plugin_instance in instances:
            name = plugin_instance.__class__.__name__

            plugin_instance.set_errortracker(self.errtracker)
            plugin_instance.set_results(results)

            try:
                data = plugin_instance.start()
            except helpers.CancelProcessing as e:
                print(f"Cancelled {self.analysis_id} processing: {e}")
                break
            except Exception as e:
                err = f"Failed to run plugin {plugin_instance}. Error: {e}"
                print(err)
                self.errtracker.set_fatal_error(err, exception=True)
                break

            if data is not None and plugin_instance.KEY:
                if plugin_instance.KEY in results:
                    raise PluginWorkerError(
                        f"Duplicate results key {plugin_instance.KEY} used by "
                        f"plugin {name}"
                    )

                results[plugin_instance.KEY] = data

        # Give plugins the chance to perform cleanup
        for plugin_instance in instances:
            try:
                plugin_instance.cleanup()
            except Exception as e:
                print(
                    f"ERROR: cleanup failed for plugin: {plugin_instance}. "
                    f"Error: {e}"
                )

        return results

    def run_reporting_plugins(self, plugins, results):
        instances = self.get_plugin_instances(plugins)

        # Run all plugin instances.
        for plugin_instance in instances:
            plugin_instance.set_errortracker(self.errtracker)
            plugin_instance.set_results(results)
            self.run_reporting_plugin(plugin_instance)

        # Give plugins the chance to perform cleanup
        for plugin_instance in instances:
            try:
                plugin_instance.cleanup()
            except Exception as e:
                print(
                    f"ERROR: cleanup failed for plugin: {plugin_instance}. "
                    f"Error: {e}"
                )

    def run_reporting_plugin(self, plugin_instance):
        report_stage_handler = plugin_instance.handlers.get(self.worktype)
        if not report_stage_handler:
            return

        try:
            report_stage_handler()
        except Exception as e:
            print(
                f"ERROR: Failure in reporting {self.worktype} stage "
                f"{report_stage_handler}. Error: {e}"
            )
            print(traceback.format_exc())

class WorkReceiver(UnixSocketServer):

    PLUGIN_BASEPATH = "cuckoo.processing"
    REPORTING_PLUGIN_PATH = "cuckoo.processing.reporting"

    def __init__(self, sockpath, worktype, name):
        self.name = name
        self.worktype = worktype
        self.reader = None
        self.work_plugins = []
        self.reporting_plugins = []
        self.state = ""

        super().__init__(sockpath)

    def start(self):
        try:
            signal.signal(signal.SIGTERM, self.cleanup)
            self.initialize_plugins()
            self.create_socket(backlog=1)
            self.start_accepting()
        except KeyboardInterrupt:
            print(f"{self.name} stopping..")

    def send_msg(self, message_dict):
        self.reader.send_json_message(message_dict)

    def initialize_plugins(self):
        try:
            work = helpers.enumerate_plugins(
                f"{self.PLUGIN_BASEPATH}.{self.worktype}", globals(),
                helpers.Processor
            )
        except ImportError as e:
            print(f"Failed to import worker plugins: {e}")
            return False

        try:
            reporting = helpers.enumerate_plugins(
                self.REPORTING_PLUGIN_PATH, globals(), helpers.Reporter
            )
        except ImportError as e:
            print(f"Failed to import reporting plugins: {e}")
            return False

        for plugin_class in work:
            plugin_class.init_once()

        for plugin_class in reporting:
            plugin_class.init_once()

        self.work_plugins = work
        self.reporting_plugins = reporting

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

    def handle_message(self, sock, m):
        try:
            w = PluginWorker(
                self.worktype, m["analysis"], m["analysis_path"],
                self.work_plugins, self.reporting_plugins,
                m.get("task_id"), m.get("binary_path")
            )
            print(f"{self.name}: Starting work!")

            w.start()

            if w.errtracker.state != w.errtracker.OK:
                self.update_state(
                    States.WORK_FAIL, {
                        "traceback": w.errtracker.fatal["traceback"],
                        "error": w.errtracker.fatal["error"]
                    }
                )
            else:
                self.update_state(States.FINISHED)
        except Exception as e:
            print(f"Worker fail: {e}")
            self.update_state(
                States.WORKER_FAIL, {
                    "traceback": traceback.format_exc(),
                    "error": e
                }
            )

        del w

class WorkerHandler(object):

    MAX_WORKERS = {
        "identification": 2,
        "pre": 2,
        "behavior": 0
    }

    def __init__(self, controller_sock_path):
        self.do_run = True
        self.unready_workers = []
        self.connected_workers = {}
        self.controller_comm = UnixSockClient(controller_sock_path)

        # Queues with work
        self.queues = {
            "identification": [],
            "pre": [],
            "behavior": []
        }

    def identify(self, analysis_id):
        self.queues["identification"].append(analysis_id)

    def pre_analysis(self, analysis_id):
        self.queues["pre"].append(analysis_id)

    def behavioral_analysis(self, analysis_id):
        self.queues["behavior"].append(analysis_id)

    def start(self):
        self.controller_comm.connect()

        for worktype, max_workers in self.MAX_WORKERS.items():
            for worker_number in range(max_workers):
                self.start_worker(f"{worktype}{worker_number}", worktype)

        try:
            self.handle_workers()
        except KeyboardInterrupt:
            print("Stopping worker handler..")
        finally:
            self.stop()

    def find_worker(self, name):
        for worker in self.connected_workers.values():
            if worker["name"] == name:
                return worker

        return None

    def stop(self):
        self.do_run = False
        for worker in self.connected_workers.values():
            try:
                worker["process"].terminate()
            except OSError:
                pass

    def start_worker(self, name, worktype):
        if name in self.connected_workers:
            raise KeyError(f"Processing worker {name} already exists")

        sockpath = Paths.unix_socket(f"{name}.sock")
        if os.path.exists(sockpath):
            print(f"Socket {sockpath} still exists. Removing..")
            os.unlink(sockpath)

        print(f"Starting worker: {name}")
        worker = WorkReceiver(sockpath, worktype, name)
        proc = multiprocessing.Process(target=worker.start)
        proc.start()

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
            print("Cannot requeue work for worker without work")
            return

        job = worker["job"]
        worktype = worker["worktype"]
        print(f"Requeuing job {job} from worker {worker['name']}")
        self.queues[worktype].insert(job)

    def stop_worker(self, worker):
        sock = worker["comm"].sock
        worker["comm"].cleanup()
        try:
            worker["process"].terminate()
        except OSError:
            pass

        self.connected_workers.pop(sock, None)

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
            if worker["state"] in (States.WORKING, States.SETUP):
                print(f"Invalid message received from worker {worker}: {e}")
                self.requeue_work(worker)
                self.stop_worker(worker)
            return

        if not msg:
            self.stop_worker(worker)
            return

        # Read the state send to us by the worker
        state = msg["state"]

        # Worker finished its current job and is ready for another.
        if state == States.FINISHED:
            self.controller_workdone(worker)

            job = worker["job"]
            worker["job"] = None
            self.set_worker_state(States.IDLE, worker)

            print(f"Worker {worker['name']} finished job: {job}")

        # Worker has set up/loaded plugins and is ready to receive a job.
        elif state == States.READY:
            print(f"Worker {worker['name']} is done setting up")
            self.set_worker_state(States.IDLE, worker)

        # A fatal error occurred during processing. Inform the controller of
        # the fail.
        elif state == States.WORK_FAIL:
            self.controller_workfail(worker)
            worker["job"] = None
            self.set_worker_state(States.IDLE, worker)

        # A unhandled exception occurred and processing and/or reporting was
        # likely abruptly stopped. Inform the controller and perform any
        # handling of the failing worker.
        elif state == States.WORKER_FAIL:
            self.controller_workfail(worker)
            # TODO: Depending on what the fail is, we might want to kill and
            # restart the worker?
            print(
                f"Fail from worker: {worker['name']}. "
                f"Error: {msg.get('error')}. "
                f"traceback: {msg.get('traceback')}"
            )

    def controller_workdone(self, worker):
        self.controller_comm.send_json_message({
            "subject": "workdone",
            "worktype": worker["worktype"],
            "work": worker["job"]
        })

    def controller_workfail(self, worker):
        self.controller_comm.send_json_message({
            "subject": "workfail",
            "worktype": worker["worktype"],
            "work": worker["job"]
        })

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

            analysis_id = queue.pop(0)
            self.assign_worker(worker, analysis_id)

    def assign_worker(self, worker, analysis_id):
        print(f"Assigning {analysis_id} to: {worker['name']}")

        worker["comm"].send_json_message({
            "analysis": analysis_id,
            "analysis_path": Paths.analysis(analysis_id),
            "binary_path": AnalysisPaths.submitted_file(analysis_id)
        })

        worker["job"] = {"analysis_id": analysis_id}
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
