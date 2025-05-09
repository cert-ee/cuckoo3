# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import threading
import queue
import time

from cuckoo.common.analyses import delete_analysis_disk
from cuckoo.common.log import CuckooGlobalLogger, TaskLogger
from cuckoo.common.strictcontainer import Task
from cuckoo.common.clients import TaskRunnerClient, ActionFailedError
from cuckoo.common.storage import TaskPaths, UnixSocketPaths, AnalysisPaths
from cuckoo.common import task
from cuckoo.common.machines import MachineListError
from cuckoo.common.errors import ErrorTracker

from .resultserver import servers

log = CuckooGlobalLogger(__name__)


class NodeError(Exception):
    pass


class TaskWorkError(NodeError):
    pass


class MachineNotAvailable(NodeError):
    pass


class NodeMsgTypes:
    TASK_STATE = "task_state"
    MACHINE_DISABLED = "machine_disabled"


class NodeTaskStates:
    TASK_FAILED = "task_failed"
    TASK_RUNNING = "task_running"
    TASK_DONE = "task_done"


class NodeStates:
    # State should be used if a node is waiting for a main to connect/give
    # work for the first time after boot or a reset.
    WAITING_MAIN = "waiting_main"
    # Node should have this state if it has performed any task work at all.
    HAS_WORKED = "has_worked"


class _TaskWork:
    def __init__(self, nodectx, task, machine):
        self.ctx = nodectx
        self.task = task
        self.machine = machine
        self.ended = False

        self._log = None

        self._closed = False
        self._errtracker = ErrorTracker()

    @property
    def errtracker(self):
        if self._closed:
            raise TaskWorkError("Cannot access errtracker. Node work already closed.")

        return self._errtracker

    @property
    def log(self):
        if self._closed:
            raise TaskWorkError("Cannot access task logger. Node work already closed")

        if not self._log:
            return log

        return self._log

    def init(self):
        self._log = TaskLogger(__name__, self.task.id)

    def set_ended(self):
        self.ended = True

    def _start_task(self):
        resultserver = servers.get()
        self.log.debug(
            "Asking taskrunner to start task",
            task_id=self.task.id,
            machine=self.machine.name,
            resultserver=resultserver,
        )
        try:
            TaskRunnerClient.start_task(
                UnixSocketPaths.task_runner(),
                kind=self.task.kind,
                task_id=self.task.id,
                analysis_id=self.task.analysis_id,
                machine=self.machine,
                resultserver=resultserver,
                rooter_sock_path=self.ctx.rooter_sock,
            )
            return True
        except ActionFailedError as e:
            self.log.error("Failed to start task.", task_id=self.task.id, error=e)
            self.task.state = task.States.FATAL_ERROR
            self.errtracker.fatal_error(f"Failed to start task. Error: {e}")

        return False

    def start(self):
        if not self._start_task():
            # Write errors to error container file. This is part of the
            # task folder and is retrieved by the main Cuckoo node.
            self._write_changes()
            self.set_ended()

    def _write_changes(self):
        if self.errtracker.has_errors():
            task.merge_errors(self.task, self.errtracker.to_container())

        # Merge errors from runerr.json. Written by taskrunner.
        task.merge_run_errors(self.task)

        if self.task.was_updated:
            task.write_changes(self.task)

    def close(self):
        if self._closed:
            return

        self._write_changes()

        if self._log:
            self.log.close()
            self._log = None

        self._closed = True


class InfoStreamReceiver:
    def task_state(self, task_id, state):
        raise NotImplementedError

    def disabled_machine(self, machine_name, reason):
        raise NotImplementedError

    def reset_stream(self):
        raise NotImplementedError


class NodeInfoStream:
    def __init__(self, stream_receiver):
        self.receiver = stream_receiver

    def reset(self):
        self.receiver.reset_stream()

    def task_state(self, task_id, state):
        self.receiver.task_state(task_id, state)

    def disabled_machine(self, machine_name, reason):
        self.receiver.disabled_machine(machine_name, reason)


class _TaskStartWorker(threading.Thread):
    def __init__(self, work_queue, task_tracker, nodectx):
        super().__init__()

        self._task_tracker = task_tracker
        self._work_queue = work_queue
        self.ctx = nodectx

        self.do_run = True

    def run(self):
        while self.do_run:
            try:
                worktracker = self._work_queue.get(timeout=1)
            except queue.Empty:
                continue

            self._task_tracker.task_started(worktracker.task.id)
            try:
                worktracker.init()
                worktracker.start()
            except Exception as e:
                worktracker.set_ended()
                worktracker.log.exception(
                    "Unexpected error when starting task.",
                    task_id=worktracker.task.id,
                    error=e,
                )
            finally:
                if worktracker.ended:
                    worktracker.close()
                    self.ctx.state_controller.task_fail(task_id=worktracker.task.id)

    def stop(self):
        self.do_run = False


class _TasksTracker:
    def __init__(self, node):
        self._node = node
        self._tasks = {}
        self._lock = threading.RLock()

    @property
    def tasks(self):
        return [taskwork for taskwork in self._tasks.values()]

    def set_state(self, task_id, state):
        with self._lock:
            self._node.infostream.task_state(task_id, state)

    def track_ongoing_taskwork(self, taskwork):
        with self._lock:
            if taskwork.task.id in self._tasks:
                raise TaskWorkError(f"Task {taskwork.task.id} is already tracked")

            self._tasks[taskwork.task.id] = taskwork

    def work_exists(self, analysis_id):
        with self._lock:
            for task_id in self._tasks.keys():
                if task_id.startswith(analysis_id):
                    return True

            return False

    def task_started(self, task_id):
        self.set_state(task_id, NodeTaskStates.TASK_RUNNING)

    def task_failed(self, task_id):
        self.task_ended(task_id, NodeTaskStates.TASK_FAILED)

    def task_done(self, task_id):
        self.task_ended(task_id, NodeTaskStates.TASK_DONE)

    def task_ended(self, task_id, state):
        with self._lock:
            taskwork = self._tasks.get(task_id)
            if not taskwork:
                raise TaskWorkError(f"Cannot mark end for unknown task: {task_id}")

            taskwork.close()
            self._node.ctx.machinery_manager.machines.release(taskwork.machine)
            self.remove_tracked_taskwork(task_id)
            self.set_state(task_id, state)

    def remove_tracked_taskwork(self, task_id):
        with self._lock:
            taskwork = self._tasks.pop(task_id)
            taskwork.close()


class Node:
    NUM_TASK_START_WORKER = 2

    def __init__(self, nodectx, stream_receiver):
        self.ctx = nodectx
        self.infostream = NodeInfoStream(stream_receiver)
        self._queue = queue.Queue()
        self._task_tracker = _TasksTracker(self)
        self._workers = []
        self.state = NodeStates.WAITING_MAIN

    def add_work(self, task_id, machine_name):
        # Set state to a state that indicates this node has performed work.
        # this is required info so that the main node can see if the node
        # needs to be reset. The main node needs the task node to be in a
        # specific state, which it can only reach through reboot or reset.
        self.state = NodeStates.HAS_WORKED
        try:
            taskfile = Task.from_file(TaskPaths.taskjson(task_id))
        except (KeyError, ValueError, TypeError) as e:
            raise TaskWorkError(
                f"Invalid or non-existing task json for task id {task_id}. {e}"
            )

        try:
            machine = self.ctx.machinery_manager.machines.acquire_available(
                task_id, machine_name
            )
        except (KeyError, MachineListError) as e:
            raise MachineNotAvailable(f"Failed to acquire machine {machine_name}. {e}")

        if not machine:
            raise MachineNotAvailable(f"Machine {machine_name} is not available")

        taskwork = _TaskWork(self.ctx, taskfile, machine)
        self._task_tracker.track_ongoing_taskwork(taskwork)
        self._queue.put(taskwork)

    def set_task_failed(self, task_id):
        self._task_tracker.task_failed(task_id)

    def set_task_success(self, task_id):
        self._task_tracker.task_done(task_id)

    def stop(self):
        for worker in self._workers:
            worker.stop()

    async def cancel_all(self):
        # Disable machinery manager and task runner from accepting new
        # work. We need to do this to prevent work coming in while we are
        # cancelling tasks.
        self.ctx.is_resetting = True
        # Get a copy of all current tasks. We need this to be able to know
        # what analysis dirs to delete when the cancel is finished.
        tasks = self._task_tracker.tasks
        log.debug("Disabling machine manager")
        self.ctx.machinery_manager.disable()
        log.debug("Disabling task runner")
        try:
            TaskRunnerClient.disable(UnixSocketPaths.task_runner())
        except ActionFailedError as e:
            raise NodeError(f"Failed to disable task runner. {e}")

        while True:
            log.debug("Waiting for work queue to be emptied")
            time.sleep(2)
            if self._queue.empty():
                log.debug("Work queue empty")
                break

        log.info("Starting cancelling of all tasks")
        try:
            TaskRunnerClient.stop_all(UnixSocketPaths.task_runner())
            while True:
                count = TaskRunnerClient.get_task_count(UnixSocketPaths.task_runner())
                if not count:
                    break

                log.debug(
                    "Waiting for task runner to finish stopping all tasks",
                    remaining=count,
                )
                time.sleep(1)
        except ActionFailedError as e:
            raise NodeError(f"Failed to all stop active tasks. {e}")

        # Wait until all pending work in the machinery manager is done before
        # we tell it to stop all machines.
        log.debug("waiting for machinery manager queue to finish work")
        self.ctx.machinery_manager.wait_work_done()

        # Stop all machines that are still running.
        self.ctx.machinery_manager.shutdown_all()

        log.debug("Removing remaining tracked tasks")
        # Remove any remaining tracked tasks.
        for taskwork in self._task_tracker.tasks:
            self._task_tracker.remove_tracked_taskwork(taskwork.task.id)

        # Delete all directories of analysis that the task work was part of.
        # Cuckoo main cannot delete this without performing a lot of extra
        # work to know what tasks were scheduled to what node if Cuckoo main
        # itself was rebooted.
        log.debug("Deleting all analysis directories of cancelled work")
        for taskwork in tasks:
            if AnalysisPaths.path(taskwork.task.analysis_id).exists():
                delete_analysis_disk(taskwork.task.analysis_id)

        # Reset stream so that all event history is cleared. Events that
        # occurred for cancelled tasks are not relevant.
        log.debug("Resetting info stream")
        await self.infostream.receiver.reset_stream()

        log.debug("Enabling machinery manager")
        self.ctx.machinery_manager.enable()
        try:
            log.debug("enabling task runner")
            TaskRunnerClient.enable(UnixSocketPaths.task_runner())
        except ActionFailedError as e:
            raise NodeError(f"Failed to enable task runner. {e}")

        self.state = NodeStates.WAITING_MAIN
        self.ctx.is_resetting = False

    def work_exists(self, analysis_id):
        return self._task_tracker.work_exists(analysis_id)

    def start(self):
        for _ in range(self.NUM_TASK_START_WORKER):
            worker = _TaskStartWorker(self._queue, self._task_tracker, self.ctx)
            self._workers.append(worker)
            worker.start()
