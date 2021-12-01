# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import threading

import queue

from cuckoo.common.log import CuckooGlobalLogger, TaskLogger
from cuckoo.common.errors import ErrorTracker
from cuckoo.common.storage import TaskPaths, Paths
from cuckoo.common.node import NodeInfos

from .nodeclient import NodeActionError, NodeUnavailableError

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

    def delete_completed_analysis(self, analysis_id):
        for node in self._get_ready_nodes():
            node.delete_completed_analysis(analysis_id)

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
        self._requeued = False

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
        # Only request task id to be removed from task queue db
        # if it has not been rescheduled.
        if not self._requeued:
            self.ctx.scheduler.unqueue_task(self.task.id)
            self.ctx.scheduler.inform_change()

        self._released = True

    def requeue(self):
        self._requeued = True
        self.ctx.state_controller.task_pending(
            task_id=self.task.id, analysis_id=self.task.analysis_id
        )
        self.ctx.scheduler.requeue_task(self.task.id)
        self.ctx.scheduler.inform_change()

    def close(self):
        # Only write errors if task has not been requeued. Otherwise
        # it might have a fatal error, causing the the reschedule to fail.
        # The error does not matter since it is rescheduled.
        if not self._requeued and self.errtracker.has_errors():
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
            except NodeUnavailableError as e:
                startable_task.log.error(
                    "Failed to start task. Node unavailable. Requeueing",
                    node=startable_task.node.name, error=e
                )
                # Requeue and close task. Normally the node client would
                # close the startable task when the tasks ends in either
                # success/complete or fail. Now we do it here because no node
                # is tracking it.
                startable_task.requeue()
                startable_task.close()
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
        self._requeue_lock = threading.Lock()
        self._requeue = set()

    def _cancel_abandoned(self, *queuedtasks):
        """Cancels all the tasks that belong to the queuedtasks. Should
        only be used on startup, before the scheduler loop starts."""
        for queuedtask in queuedtasks:
            log.warning("Cancelling abandoned task", task_id=queuedtask.id)
            errrs = ErrorTracker()
            errrs.fatal_error("Cancelled by scheduler")
            errrs.to_file(TaskPaths.runerr_json(queuedtask.id))
            self.ctx.state_controller.task_failed(
                task_id=queuedtask.id, analysis_id=queuedtask.analysis_id
            )

        # Remove all cancelled task from the task queue.
        self.taskqueue.remove(*[t.id for t in queuedtasks])

    def _recover_abandoned(self, *queuedtasks):
        """Recovers all the tasks that belong to the queuedtasks. The
        scheduler can reschedule the tasks again after this. Should
        only be used on startup, before the scheduler loop starts."""
        for queuedtask in queuedtasks:
            log.warning("Recovering abandoned task", task_id=queuedtask.id)
            self.ctx.state_controller.task_pending(
                task_id=queuedtask.id, analysis_id=queuedtask.analysis_id
            )

        # Mark all recovered tasks as unscheduled again. The scheduler can now
        # pick them up again and schedule them on a node.
        self.taskqueue.mark_unscheduled(*[t.id for t in queuedtasks])

    def handle_abandoned(self, cancel=True):
        queued_abandoned = self.taskqueue.get_scheduled()
        if not queued_abandoned:
            return

        log.info("Found abandoned tasks", amount=len(queued_abandoned))
        if cancel:
            self._cancel_abandoned(*queued_abandoned)
        else:
            self._recover_abandoned(*queued_abandoned)

    def unqueue_task(self, task_id):
        with self._completed_lock:
            self._completed.add(task_id)

    def requeue_task(self, task_id):
        with self._requeue_lock:
            self._requeue.add(task_id)

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

    def _requeue_tasks(self):
        with self._requeue_lock:
            requeue = self._requeue.copy()

        # Mark all given 'requeue' task ids as unscheduled. This will cause
        # them to be rescheduled when the resources for it are available.
        self.taskqueue.mark_unscheduled(*requeue)
        with self._requeue_lock:
            self._requeue = self._requeue - requeue

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

                # We have assigned work to at least 1 machine here. Ensure
                # more machines are available before trying to schedule more.
                if not self.ctx.nodes.machines_available():
                    return

    def inform_change(self):
        self._change_event.set()

    def start(self):
        for _ in range(self.NUM_TASK_STARTERS):
            starter = TaskStarter(self.ctx, self._startables_queue)
            self._task_starters.append(starter)
            starter.start()

        self._change_event.set()
        log.info("Scheduler started")
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

            # Mark tasks in the requeue set as unscheduled again in the task
            # queue db. Tasks can get added to this set when their node fails.
            if self._requeue:
                self._requeue_tasks()

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
