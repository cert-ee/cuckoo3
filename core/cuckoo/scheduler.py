# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import threading

import queue

from cuckoo.common.log import CuckooGlobalLogger, TaskLogger
from cuckoo.common.errors import ErrorTracker
from cuckoo.common.storage import TaskPaths, Paths
from cuckoo.common.node import NodeInfos

from .nodeclient import NodeActionError

log = CuckooGlobalLogger(__name__)


class SchedulerError(Exception):
    pass

class NodesTracker:

    def __init__(self, cuckooctx):
        self.ctx = cuckooctx
        self._nodes = []
        self.nodeinfos = NodeInfos(min_dump_wait=300)

    @property
    def machine_lists(self):
        return [node.machines for node in self._get_ready_nodes()]

    def _get_ready_nodes(self):
        nodes = []
        for node in self._nodes:
            if not node.ready:
                log.warning("Node not ready for use", node=node.name)
                continue

            nodes.append(node)

        return nodes

    def machines_available(self):
        total = 0
        for node in self._get_ready_nodes():
            total += node.machines.available_count

        return total > 0

    def add_node(self, node):
        self._nodes.append(node)

    def notready_cb(self, node):
        self.nodeinfos.remove_nodeinfo(node.info)
        self.ctx.scheduler.inform_change()

    def ready_cb(self, node):
        self.nodeinfos.add_nodeinfo(node.info)
        self.ctx.scheduler.inform_change()

    def find_available(self, queued_task):
        """Find a node that has the machine and route the queued task
        needs."""
        for node in self._get_ready_nodes():
            if not node.info.has_route(queued_task.route):
                continue

            machine = node.machines.acquire_available(
                queued_task.id, platform=queued_task.platform,
                os_version=queued_task.os_version,
                tags=queued_task.machine_tags
            )
            if not machine:
                continue

            return machine, node

        return None, None

class StartableTask:

    def __init__(self, cuckooctx, queued_task, machine, node):
        self.ctx = cuckooctx
        self.task = queued_task
        self.machine = machine
        self.node = node

        self.errtracker = ErrorTracker()
        self._logger = None
        self._released = False

    @property
    def log(self):
        if not self._logger:
            self._logger = TaskLogger( __name__, self.task.id)

        return self._logger

    def task_running(self):
        self.ctx.state_controller.task_running(
            task_id=self.task.id, analysis_id=self.task.analysis_id,
            machine=self.machine, node=self.node
        )

    def assign_to_node(self):
        self.node.add_task(self)

    def release_resources(self):
        if self._released:
            return

        self.node.machines.release(self.machine)
        self.ctx.scheduler.unqueue_task(self.task.id)
        self.ctx.scheduler.inform_change()
        self._released = True

    def close(self):
        if self.errtracker.has_errors():
            self.errtracker.to_file(TaskPaths.runerr_json(self.task.id))
        if self._logger:
            self._logger.close()

        self.release_resources()

class TaskStarter(threading.Thread):

    def __init__(self, cuckooctx, workqueue):
        super().__init__()
        self.workqueue = workqueue
        self.ctx = cuckooctx

        self._do_run = True

    def stop(self):
        self._do_run = False

    def run(self):

        while self._do_run:
            try:
                startable_task = self.workqueue.get(timeout=1)
            except queue.Empty:
                continue

            log.info(
                "Assigning startable task to node",
                task_id=startable_task.task.id, node=startable_task.node.name,
                machine=startable_task.machine.name
            )
            try:
                startable_task.assign_to_node()
            except NodeActionError as e:
                startable_task.log.error(
                    "Failed to start task", task_id=startable_task.task.id,
                    error=e
                )
                startable_task.errtracker.fatal_error(
                    f"Failed to start task: {e}"
                )
                startable_task.node.task_failed(startable_task.task.id)
            except Exception as e:
                log.exception(
                    "Unexpected failure while starting task",
                    task_id=startable_task.task.id, error=e
                )
                startable_task.node.task_failed(
                    startable_task.task.id
                )
            else:
                startable_task.task_running()

class Scheduler:

    NUM_TASK_STARTERS = 1

    def __init__(self, cuckooctx, taskqueue):
        self.do_run = True
        self.ctx = cuckooctx
        self.taskqueue = taskqueue

        self._task_starters = []
        self._assigned_machines = {}
        self._change_event = threading.Event()
        self._startables_queue = queue.Queue()
        self._completed_lock = threading.Lock()
        self._completed = set()

    def unqueue_task(self, task_id):
        with self._completed_lock:
            self._completed.add(task_id)

    def queue_task(self, task_id, kind, created_on, analysis_id, priority,
                   platform, os_version, machine_tags, route):
        self.taskqueue.queue_task(
            task_id, kind, created_on, analysis_id, priority, platform,
            os_version, machine_tags, route
        )
        self._change_event.set()

    def queue_many(self, *task_dicts):
        self.taskqueue.queue_many(*task_dicts)
        self._change_event.set()

    def _queue_startable(self, startable_task):
        if not self.do_run:
            raise SchedulerError("Scheduler not running")

        if not self._task_starters:
            raise SchedulerError("No task starters")

        self._startables_queue.put(startable_task)

    def _unqueue_tasks(self):
        with self._completed_lock:
            completed = self._completed.copy()

        # Remove all task ids marked as completed from the queue and
        # update the completed task ids set afterwards. We do this because
        # it can change while we are deleting. We do not want to keep it
        # locked because this can stop node clients from working.
        self.taskqueue.remove(*completed)
        with self._completed_lock:
            self._completed = self._completed - completed

    def assign_work(self):
        with self.taskqueue.get_workfinder() as wf:
            for task in wf.get_unscheduled_tasks():
                machine, node = self.ctx.nodes.find_available(task)
                if not machine:
                    wf.ignore_similar_tasks(task)
                    continue

                # Add work to task starter worker queue
                try:
                    log.debug(
                        "Adding entry to task starter queue", task_id=task.id,
                        machine=machine.name, node=node.name
                    )
                    self._queue_startable(
                        StartableTask(self.ctx, task, machine, node)
                    )
                except SchedulerError as e:
                    log.warning(
                        "Failed to add entry to starter worker queue", error=e
                    )
                    return

                wf.mark_scheduled(task)

    def inform_change(self):
        self._change_event.set()

    def start(self):
        for _ in range(self.NUM_TASK_STARTERS):
            starter = TaskStarter(self.ctx, self._startables_queue)
            self._task_starters.append(starter)
            starter.start()

        self._change_event.set()
        while self.do_run:
            self._change_event.wait(timeout=60)

            # Verify if we should run again as a lot can change in the
            # timeout period.
            if not self.do_run:
                break

            # Check if a node infos dump should be made. Dump is used
            # by other components to see the available platforms, routes etc
            # for all nodes.
            if self.ctx.nodes.nodeinfos.should_dump():
                self.ctx.nodes.nodeinfos.make_dump(
                    Paths.nodeinfos_dump()
                )

            # Remove tasks from the task queue db. These tasks have been
            # marked completed/unqueued by node clients closing the
            # StartableTask
            if self._completed:
                self._unqueue_tasks()

            # Only continue to search for machines if the task queue is not
            # empty.
            if self.taskqueue.size < 1:
                log.debug("No new tasks(s)")
                self._change_event.clear()
                continue

            if not self.ctx.nodes.machines_available():
                log.debug("No available machines")
                self._change_event.clear()
                continue

            # There are tasks and one or mode machines available. Find
            # work for these idle machines.
            log.debug("Searching for work to assign")
            if not self.assign_work():
                # If no tasks were started, this means no machines that are
                # are currently available can run any of the queued tasks. Wait
                # until new tasks are submitted or a machine is unlocked.
                self._change_event.clear()

    def stop(self):
        if not self.do_run and not self._task_starters:
            return

        self.do_run = False

        # Set events so it won't block on these when stopping
        self._change_event.set()

        for starter in self._task_starters:
            starter.stop()
