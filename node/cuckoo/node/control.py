# Copyright (C) 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import queue
import threading

from cuckoo.common.storage import TaskPaths
from cuckoo.common.ipc import UnixSocketServer, ReaderWriter
from cuckoo.common.log import CuckooGlobalLogger

from cuckoo.common.importing import TaskResultZipper, AnalysisImportError

log = CuckooGlobalLogger(__name__)


class NodeStateControlError(Exception):
    pass


def _handle_task_failed(worktracker):
    worktracker.ctx.node.set_task_failed(worktracker.task_id)

def _handle_task_success(worktracker):
    worktracker.ctx.node.set_task_success(worktracker.task_id)


def _handle_state(worktracker, state):
    if worktracker.ctx.zip_results:
        zipper = TaskResultZipper(worktracker.task_id)

        try:
            zipper.make_zip(TaskPaths.zipped_results(worktracker.task_id))
        except AnalysisImportError as e:
            log.exception(
                "Failed to create task result zip.",
                task_id=worktracker.task_id, error=e
            )
            _handle_task_failed(worktracker)
            return

    if state == "success":
        _handle_task_success(worktracker)
    elif state == "failed":
        _handle_task_failed(worktracker)
    else:
        raise NodeStateControlError(f"Cannot handle unexpected state: {state}")

class _WorkTracker:

    def __init__(self, nodectx, func, **kwargs):
        self.ctx = nodectx
        self.func = func
        self.func_args = kwargs
        self.task_id = kwargs.pop("task_id", None)

    def run_work(self):
        self.func(self, **self.func_args)

    def close(self):
        pass


class StateControllerWorker(threading.Thread):

    def __init__(self, work_queue):
        super().__init__()

        self.work_queue = work_queue
        self.do_run = True

    def run(self):
        while self.do_run:
            try:
                worktracker = self.work_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                worktracker.run_work()
            except Exception as e:
                log.exception(
                    "Failed to run handler function",
                    function=worktracker.func, args=worktracker.func_args,
                    error=e
                )
                try:
                    worktracker.ctx.node.set_task_failed(worktracker.task_id)
                except Exception as e:
                    log.exception(
                        "Failed to set task to failed after failure",
                        function=worktracker.func, args=worktracker.func_args,
                        error=e
                    )
            finally:
                worktracker.close()

    def stop(self):
        self.do_run = False


class NodeTaskController(UnixSocketServer):

    NUM_STATE_CONTROLLER_WORKERS = 4
    
    def __init__(self, controller_sock_path, nodectx):
        super().__init__(controller_sock_path)

        self.ctx = nodectx
        self.workers = []
        self.work_queue = queue.Queue()
        self.subject_handler = {
            "taskrundone": self.task_done,
            "taskrunfailed": self.task_fail,
        }

    def queue_call(self, func, **kwargs):
        if not isinstance(kwargs, dict):
            raise TypeError(
                f"Kwargs dict must be a dict. Got: {type(kwargs)}"
            )

        self.work_queue.put(_WorkTracker(self.ctx, func, **kwargs))

    def task_done(self, **kwargs):
        self.queue_call(
            _handle_state, task_id=kwargs["task_id"], state="success"
        )

    def task_fail(self, **kwargs):
        self.queue_call(
            _handle_state, task_id=kwargs["task_id"], state="failed"
        )

    def handle_connection(self, sock, addr):
        self.track(sock, ReaderWriter(sock))

    def handle_message(self, sock, msg):
        subject = msg.get("subject")
        if not subject:
            return

        handler = self.subject_handler.get(subject)
        if not handler:
            return

        try:
            handler(**msg)
        except KeyError as e:
            log.warning("Incomplete message received.", msg=repr(msg), error=e)
        except TypeError as e:
            log.warning("Incorrect message received.", msg=repr(msg), error=e)
        except Exception as e:
            log.exception(
                "Fatal error while handling message.",
                error=e, message=repr(msg)
            )
            raise

    def stop(self):
        if not self.do_run and not self.workers:
            return

        super().stop()
        for worker in self.workers:
            worker.stop()

        self.cleanup()

    def start(self):
        for _ in range(self.NUM_STATE_CONTROLLER_WORKERS):
            worker = StateControllerWorker(self.work_queue)
            self.workers.append(worker)
            worker.start()

        self.create_socket()
        self.start_accepting(select_timeout=1)
