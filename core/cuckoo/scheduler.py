# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from collections import namedtuple
from threading import RLock, Event

from cuckoo.common.clients import TaskRunnerClient, ActionFailedError
from cuckoo.common.config import cfg
from cuckoo.common.storage import Paths
from cuckoo.common.log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

from .machinery import acquire_available, get_available, unlock

class _TaskQueue:
    """Dummy-ish queue. Will be exchange later for a more fitting future-proof
    queue solution."""
    # TODO ^

    _queued_task = namedtuple(
        "QueuedTask",
        ["id", "analysis_id", "priority", "created_on", "platform",
         "os_version", "kind"]
    )

    def __init__(self):
        self._lock = RLock()
        self._queue = []

    @property
    def size(self):
        with self._lock:
            return len(self._queue)

    def _sort_queue(self):
        # Ugly, slow sort for now.
        # sort on prio and create datetime
        self._queue.sort(key=lambda r: r.created_on)
        self._queue.sort(key=lambda r: r.priority, reverse=True)

    def queue_one(self, task_id, analysis_id, kind, priority, created_on,
                  platform, os_version=""):
        with self._lock:
            self._add_entry(
                task_id, analysis_id, kind, priority, created_on, platform,
                os_version
            )
            self._sort_queue()

    def queue_many(self, task_list):
        """Task list can be a list of dicts or any obj that has the attributes
        listed in 'QueuedTask'"""
        with self._lock:
            for task in task_list:
                if isinstance(task, dict):
                    self._add_entry(
                        task_id=task["id"],
                        analysis_id=task["analysis_id"],
                        kind=task["kind"],
                        priority=task["priority"],
                        created_on=task["created_on"],
                        platform=task["platform"],
                        os_version=task["os_version"]
                    )
                else:
                    self._add_entry(
                        task_id=task.id,
                        analysis_id=task.analysis_id,
                        kind=task.kind,
                        priority=task.priority,
                        created_on=task.created_on,
                        platform=task.platform,
                        os_version=task.os_version
                    )
            self._sort_queue()

    def _add_entry(self, task_id, analysis_id, kind, priority, created_on,
                   platform, os_version=""):
        with self._lock:
            self._queue.append(self._queued_task(
                id=task_id, analysis_id=analysis_id, priority=priority,
                created_on=int(created_on.timestamp()), platform=platform,
                kind=kind, os_version=os_version
            ))

    def find_work(self):
        # Search queue for task that needs platform, pop, and return it.
        with self._lock:
            for index, task in enumerate(self._queue):
                machine = acquire_available(
                    task_id=task.id, platform=task.platform,
                    os_version=task.os_version
                )
                if machine:
                    return self._queue.pop(index), machine

        return None, None


task_queue = _TaskQueue()

class Scheduler:

    def __init__(self):
        self.do_run = True

        self._assigned_machines = {}
        self._unlock_event = Event()
        self._newtasks_event = Event()

    def start_task(self, task, machine):
        log.info(
            "Requesting task runner to start task.",
            task_id=task.id, machine=machine.name
        )

        self._assigned_machines[task.id] = machine
        try:
            TaskRunnerClient.start_start(
                Paths.unix_socket("taskrunner.sock"), kind=task.kind,
                task_id=task.id, analysis_id=task.analysis_id,
                machine=machine,
                result_ip=cfg("cuckoo", "resultserver", "listen_ip"),
                result_port=cfg("cuckoo", "resultserver", "listen_port")
            )
        except ActionFailedError as e:
            log.error("Failed to start task.", task_id=task.id, error=e)
            self.task_ended(task.id)

    def task_ended(self, task_id):
        machine = self._assigned_machines.pop(task_id, None)
        if not machine:
            return

        unlock(machine)
        self._unlock_event.set()

    def newtask(self):
        self._newtasks_event.set()

    def start(self):
        while self.do_run:
            if task_queue.size < 1:
                log.debug("No new tasks")
                self._newtasks_event.clear()
                self._newtasks_event.wait(timeout=60)
                continue

            available = get_available()
            if not available:
                log.debug("No available machines")
                self._unlock_event.clear()
                self._unlock_event.wait(timeout=10)
                continue

            for _ in range(len(available)):
                task, machine = task_queue.find_work()
                if not task:
                    break

                self.start_task(task, machine)

    def stop(self):
        self.do_run = False

        # Set events so it won't block on these when stopping
        self._unlock_event.set()
        self._newtasks_event.set()
