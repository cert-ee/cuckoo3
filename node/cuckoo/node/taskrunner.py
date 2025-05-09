# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import logging
import socket
import time
from threading import Thread

from cuckoo.common.clients import (
    ResultServerClient,
    ActionFailedError,
    RooterClient,
    ClientError,
)
from cuckoo.common.errors import ErrorTracker
from cuckoo.common.guest import Agent, WaitTimeout
from cuckoo.common.ipc import (
    UnixSocketServer,
    ReaderWriter,
    message_unix_socket,
    IPCError,
)
from cuckoo.common.log import CuckooGlobalLogger, TaskLogger, exit_error
from cuckoo.common.machines import Machine
from cuckoo.common.node import ExistingResultServer
from cuckoo.common.shutdown import register_shutdown
from cuckoo.common.startup import init_global_logging
from cuckoo.common.storage import (
    AnalysisPaths,
    TaskPaths,
    Paths,
    cuckoocwd,
    UnixSocketPaths,
)
from cuckoo.common.strictcontainer import Task, Analysis
from cuckoo.common.taskflow import TaskFlowError
from .taskflow import StandardTask

log = CuckooGlobalLogger(__name__)


class _FlowRunner(Thread):
    """Runs a given taskflow in a thread"""

    def __init__(
        self,
        taskflow_cls,
        task_id,
        analysis_id,
        machine,
        resultserver,
        rooter_sock_path=None,
    ):
        super().__init__()
        self.taskflow_cls = taskflow_cls
        self.machine = machine
        self.resultserver = resultserver

        self.task = Task.from_file(TaskPaths.taskjson(task_id))
        self.analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
        self.agent = Agent(self.machine.ip, self.machine.agent_port)
        self.taskflow = taskflow_cls(
            self.machine,
            self.task,
            self.analysis,
            self.agent,
            resultserver,
            TaskLogger(__name__, task_id),
        )
        self.do_run = True

        self.errtracker = ErrorTracker()

        if rooter_sock_path and not isinstance(rooter_sock_path, str):
            raise TypeError("Rooter socket path must be a string")

        self.rooter_sock_path = rooter_sock_path
        self.route_request = None

        self.setName(f"Flowrunner_{self.taskflow_cls.name}_Task_{self.task.id}")

    def task_success(self):
        self.taskflow.log.debug("Sending task done state to state controller")
        try:
            message_unix_socket(
                UnixSocketPaths.node_state_controller(),
                {
                    "subject": "taskrundone",
                    "analysis_id": self.analysis.id,
                    "task_id": self.task.id,
                },
            )
            self.taskflow.log.info("Task completed.")
        except IPCError as e:
            log.error("Failed to send task done to state controller.", error=e)

    def task_failed(self):
        self.taskflow.log.debug("Sending task failed state to state controller")
        try:
            message_unix_socket(
                UnixSocketPaths.node_state_controller(),
                {
                    "subject": "taskrunfailed",
                    "analysis_id": self.analysis.id,
                    "task_id": self.task.id,
                },
            )
            self.taskflow.log.info("Task failed.")
        except IPCError as e:
            log.error("Failed to send task fail to state controller.", error=e)

    def run_until_timeout(self):
        timeout = self.analysis.settings.timeout
        self.taskflow.log.debug("Running until timeout", timeout=timeout)
        start = time.monotonic()
        while self.do_run:
            self.taskflow.call_at_interval()

            total_passed = time.monotonic() - start
            if total_passed >= timeout:
                self.taskflow.log.debug("Task run timeout reached", timeout=timeout)
                break

            time.sleep(self.taskflow.INTERVAL_CALL_WAIT)

    def remove_from_resultserver(self):
        try:
            ResultServerClient.remove(
                self.resultserver.socket_path, self.machine.ip, self.task.id
            )
        except ActionFailedError as e:
            self.taskflow.log.error(
                "Failed to remove IP-task mapping from resultserver.", error=e
            )
            self.errtracker.fatal_error(
                f"Failed to remove ip {self.machine.ip} from resultserver for "
                f"task {self.task.id}. {e}"
            )

    def stop_machine(self):
        try:
            self.taskflow.stop_machine()
        except TaskFlowError as e:
            self.taskflow.log.error("Error during machine stop request", error=e)
            self.errtracker.fatal_error(e)
        except Exception as e:
            self.taskflow.log.exception(
                "Unhandled error during machine stop request", error=e
            )
            self.errtracker.fatal_exception(
                f"Unhandled error during machine stop request: {e}",
            )

    def _request_route(self):
        if not self.rooter_sock_path or not self.task.route:
            return

        self.taskflow.log.debug(
            "Requesting rooter to apply route", route=self.task.route
        )
        try:
            self.route_request = RooterClient.request_route(
                self.rooter_sock_path, self.task.route, self.machine, self.resultserver
            )
        except ClientError as e:
            raise TaskFlowError(f"Failure during rooter route request: {e}")

    def run(self):
        log.info(
            "Task starting.",
            task_id=self.task.id,
            machine=self.machine.name,
            target=repr(self.taskflow.analysis.target.target),
        )

        # Dump the received machine to the task root directory to be read if
        # machine information is required during post task processing.
        self.machine.to_file(TaskPaths.machinejson(self.task.id))

        try:
            self.run_steps()
        except TaskFlowError as e:
            self.errtracker.fatal_error(e)
            self.taskflow.log.error("Error during task run", error=e)
        except Exception as e:
            self.errtracker.fatal_exception(f"Unhandled error: {e}")
            self.taskflow.log.exception("Unhandled error during task run", error=e)
        finally:
            self.taskflow.log.debug(
                "Requesting machine stop", machine=self.machine.name
            )
            self.stop_machine()

            self.taskflow.log.debug(
                "Asking resultserver to unmap IP-task", ip=self.machine.ip
            )
            self.remove_from_resultserver()

            if self.route_request:
                self.taskflow.log.debug(
                    "Asking rooter to disable requested route",
                    route=self.route_request.route,
                )
                self.route_request.disable_route()

            if self.errtracker.has_errors():
                self.errtracker.to_file(TaskPaths.runerr_json(self.task.id))

        if not self.errtracker.has_fatal():
            self.task_success()
        else:
            self.task_failed()
        self.taskflow.log.close()

    def run_steps(self):
        self.taskflow.log.debug(
            "Asking resultserver to map for IP to task", ip=self.machine.ip
        )
        try:
            ResultServerClient.add(
                self.resultserver.socket_path, self.machine.ip, self.task.id
            )
        except ActionFailedError as e:
            raise TaskFlowError(
                f"Failed to add ip {self.machine.ip} to resultserver for "
                f"task {self.task.id}. {e}"
            )

        self.taskflow.log.debug(
            "Initializing taskflow", taskflowkind=self.taskflow_cls.name
        )
        self.taskflow.initialize()

        # Start the machine however this flow wants to start the machine
        self.taskflow.log.debug("Requesting machine start.", machine=self.machine.name)
        self.taskflow.start_machine()

        # TODO get timeout from config
        # Wait until the agent in the machine is online and then give
        # control back to the task flow
        self.taskflow.log.debug(
            "Waiting until agent is online.",
            agent_address=f"{self.machine.ip}:{self.machine.agent_port}",
        )
        timeout = 120
        try:
            self.agent.wait_online(timeout=timeout)
        except WaitTimeout as e:
            raise TaskFlowError(
                f"Agent not online within timeout of {timeout} seconds. {e}"
            )

        # Task flow can now prepare the machine
        self.taskflow.log.debug("Agent online")

        # Request rooter to apply route if we received a rooter path and the
        # current task has a route.
        self._request_route()

        self.taskflow.machine_online()
        self.run_until_timeout()

    def stop(self):
        self.do_run = False


_supported_flowkinds = {StandardTask.name: StandardTask}


class TaskRunner(UnixSocketServer):
    """Accepts new tasks to run. Looks up a task flow for the matching
    task kind and runs the flow in a _FlowRunner."""

    _MIN_KEYS = {"task_id", "analysis_id", "kind", "resultserver", "machine"}

    def __init__(self, sockpath, cuckoocwd, loglevel=logging.DEBUG):
        super().__init__(sockpath)

        self.cuckoocwd = cuckoocwd
        self.loglevel = loglevel

        self.active_flows = []
        self.responses = []
        self.enabled = True

    def handle_connection(self, sock, addr):
        self.track(sock, ReaderWriter(sock))

    def start_new_taskflow(
        self, task_id, analysis_id, kind, resultserver, machine, rooter_sock_path=None
    ):
        taskflow_cls = _supported_flowkinds.get(kind)
        if not taskflow_cls:
            raise TaskFlowError(f"Flow kind {kind!r} not supported")

        try:
            m = Machine.from_dict(machine)
            rs = ExistingResultServer.from_dict(resultserver)
            flowrunner = _FlowRunner(
                taskflow_cls, task_id, analysis_id, m, rs, rooter_sock_path
            )
        except Exception as e:
            log.exception("Failure during task flow runner initialization", error=e)
            raise TaskFlowError(
                f"Fatal error. Failed to initialize task flow runner. Error: {e}"
            )

        flowrunner.daemon = True
        self.active_flows.append(flowrunner)
        flowrunner.start()

    def stop_all_taskflows(self):
        for flowrunner in self.active_flows[:]:
            flowrunner.stop()
            log.info("Cancelled task run", task_id=flowrunner.task.id)

    def _do_new_task(self, sock, msg):
        readerwriter = self.socks_readers[sock]
        if not self.enabled:
            self.responses.append(
                (readerwriter, {"success": False, "reason": "Task runner is disabled"})
            )
            self.untrack(sock)
            return

        kwargs = msg.get("args", {})
        if not kwargs or not self._MIN_KEYS.issubset(set(kwargs.keys())):
            log.debug("Invalid request received. Missing keys.", received=repr(msg))
            self.untrack(sock)
            return

        task_id = kwargs["task_id"]
        try:
            self.start_new_taskflow(**kwargs)
            self.responses.append((readerwriter, {"success": True}))
        except TaskFlowError as e:
            log.error("Failed to start taskflow", task_id=task_id, error=e)
            self.responses.append((readerwriter, {"success": False, "reason": str(e)}))
            return
        except Exception as e:
            log.exception(
                "Fatal error. Failed to start taskflow.", task_id=task_id, error=e
            )
            self.responses.append((readerwriter, {"success": False, "reason": str(e)}))
            return

    def _do_enable_disable(self, sock, action):
        readerwriter = self.socks_readers[sock]
        if action == "disable":
            self.enabled = False
            log.warning("Task runner disable by request")
        elif action == "enable":
            self.enabled = True
            log.warning("Task runner enabled by request")

        self.responses.append((readerwriter, {"success": True}))

    def _do_send_flowscount(self, sock):
        readerwriter = self.socks_readers[sock]
        self.responses.append((readerwriter, {"count": len(self.active_flows)}))

    def handle_message(self, sock, msg):
        action = msg.get("action")
        if action == "starttask":
            self._do_new_task(sock, msg)
        elif action == "stopall":
            self.stop_all_taskflows()
            self.responses.append((self.socks_readers[sock], {"success": True}))
        elif action in ("disable", "enable"):
            self._do_enable_disable(sock, action)
        elif action == "getflowcount":
            self._do_send_flowscount(sock)
        else:
            log.debug("Invalid action request received", received=repr(msg))
            self.untrack(sock)

    def check_flow_statuses(self):
        for flowrunner in self.active_flows[:]:
            if not flowrunner.is_alive():
                self.active_flows.remove(flowrunner)

    def timeout_action(self):
        for rw_response in self.responses[:]:
            self.responses.remove(rw_response)
            readerwriter, response = rw_response

            try:
                readerwriter.send_json_message(response)
            except socket.error as e:
                log.debug(
                    "Failed to send response task request.", response=response, error=e
                )
                self.untrack(readerwriter.sock)
                continue

        self.check_flow_statuses()

    def stop(self):
        if not self.do_run and not self.active_flows:
            return

        super().stop()
        self.stop_all_taskflows()

        self.cleanup()

    def start(self):
        cuckoocwd.set(self.cuckoocwd.root, analyses_dir=self.cuckoocwd.analyses)
        register_shutdown(self.stop)

        init_global_logging(self.loglevel, Paths.log("cuckoo.log"), use_logqueue=False)

        try:
            self.create_socket()
        except IPCError as e:
            exit_error(f"Failed to create unix socket: {e}")

        self.start_accepting()

        # Join flowrunner threads that are still alive to cause a more clean
        # stop.
        for flowrunner in self.active_flows[:]:
            if not flowrunner.is_alive():
                continue

            log.info("Waiting for task flow to stop.", task_id=flowrunner.task.id)

            timeout = 10
            flowrunner.join(timeout=10)
            if flowrunner.is_alive():
                log.warning(
                    "Task flow did not stop within timeout.",
                    task_id=flowrunner.task.id,
                    timeout=timeout,
                )
