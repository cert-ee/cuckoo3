# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import queue
import threading
import traceback

from cuckoo.common.ipc import UnixSocketServer, ReaderWriter
from cuckoo.common.storage import Paths, AnalysisPaths
from cuckoo.common.strictcontainer import Analysis, Identification
from cuckoo.common.log import CuckooGlobalLogger

from . import analyses, db, started, task
from .scheduler import task_queue

log = CuckooGlobalLogger(__name__)

def track_untracked():
    analysis_ids = os.listdir(Paths.untracked())
    if not analysis_ids:
        return

    valid_untracked = []
    for untracked_id in analysis_ids:
        untracked_path = Paths.analysis(untracked_id)
        if not os.path.isdir(untracked_path):
            log.error(
                "Cannot track new analysis ID. Analysis path does not exist",
                analysis_path=untracked_path
            )
            continue

        valid_untracked.append(untracked_id)

    analyses.track_analyses(valid_untracked)
    log.info("Tracked new analyses.", amount=len(valid_untracked))
    for tracked in valid_untracked:
        started.processing_handler.identify(tracked)
        os.unlink(Paths.untracked(tracked))


def handle_identification_done(analysis_id):
    analysis = Analysis.from_file(
        AnalysisPaths.analysisjson(analysis_id)
    )
    if analysis.settings.manual:
        db.set_analysis_state(
            analysis_id, db.AnalysisStates.WAITING_MANUAL
        )
    else:
        ident = Identification.from_file(AnalysisPaths.identjson(analysis_id))

        if ident.selected:
            db.set_analysis_state(
                analysis_id, db.AnalysisStates.PENDING_PRE
            )
            started.processing_handler.pre_analysis(analysis_id)
        else:
            db.set_analysis_state(
                analysis_id, db.AnalysisStates.NO_SELECTED
            )

def handle_pre_done(analysis_id):
    analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))

    # We currently only use the identified platforms and tags if the user
    # did not supply either. TODO improve this and move logic to location
    # where the analysis json is already being stored. TODO tags will be per
    # platform/analysis machine. Combine tags when tasks are created
    if not analysis.settings.platforms and not analysis.settings.machine_tags:
        ident = Identification.from_file(AnalysisPaths.identjson(analysis_id))

        analyses.update_settings(
            analysis, platforms=ident.target.platforms,
            machine_tags=ident.target.machine_tags
        )
        analysis.to_file(AnalysisPaths.analysisjson(analysis_id))

    log.debug("Creating tasks for analysis.", analysis_id=analysis_id)
    try:
        tasks = task.create_all(analysis)
    except task.TaskCreationError as e:
        log.error(
            "Failed to create tasks for analysis.",
            analysis_id=analysis_id, error=e
        )
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)
        return

    db.set_analysis_state(analysis_id, db.AnalysisStates.COMPLETED_PRE)
    task_queue.queue_many(tasks)
    started.scheduler.newtask()

def set_next_state(worktype, analysis_id, task_id=None):
    if worktype == "identification":
        analyses.merge_ident_errors(analysis_id)
        handle_identification_done(analysis_id)

    elif worktype == "pre":
        analyses.merge_pre_errors(analysis_id)
        handle_pre_done(analysis_id)

def set_failed(worktype, analysis_id, task_id=None):
    if worktype == "identification":
        log.error(
            "Analysis identification stage failed", analysis_id=analysis_id
        )
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)
        analyses.merge_ident_errors(analysis_id)

    elif worktype == "pre":
        log.error("Analysis pre stage failed", analysis_id=analysis_id)
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)
        analyses.merge_pre_errors(analysis_id)

    else:
        raise ValueError(
            f"Unknown work type {worktype} for analysis: {analysis_id}"
        )

def handle_task_done(task_id):
    log.info("Setting task to state reported", task_id=task_id)
    started.scheduler.task_ended(task_id)
    task.set_db_state(task_id, db.TaskStates.REPORTED)
    task.merge_run_errors(task_id)

def set_task_failed(task_id):
    log.error("Setting task to state failed", task_id=task_id)
    started.scheduler.task_ended(task_id)
    task.set_db_state(task_id, db.TaskStates.FATAL_ERROR)
    task.merge_run_errors(task_id)


class StateControllerWorker(threading.Thread):

    def __init__(self, work_queue):
        super().__init__()

        self.work_queue = work_queue
        self.do_run = True

    def run(self):
        while self.do_run:
            try:
                func, kwargs = self.work_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                func(**kwargs)
            except Exception as e:
                log.exception(
                    "Failed to run handler function.",
                    function=func, args=kwargs, error=e
                )

    def stop(self):
        self.do_run = False


class StateController(UnixSocketServer):

    # Keep amount of worker to 1 for now to prevent db locking issues with
    # sqlite. 1 thread should be enough.
    NUM_STATE_CONTROLLER_WORKERS = 1
    
    def __init__(self, controller_sock_path):
        super().__init__(controller_sock_path)

        self.workers = []
        self.work_queue = queue.Queue()
        self.subject_handler = {
            "tracknew": self.track_new_analyses,
            "workdone": self.work_done,
            "workfail": self.work_failed,
            "taskrundone": self.task_done,
            "taskrunfailed": self.task_failed
        }

    def queue_call(self, func, kwargsdict={}):
        if not isinstance(kwargsdict, dict):
            raise TypeError(
                f"Kwargs dict must be a dict. Got: {type(kwargsdict)}"
            )

        self.work_queue.put((func, kwargsdict))

    def work_done(self, **kwargs):
        self.queue_call(
            set_next_state, {
                "worktype": kwargs["worktype"],
                "analysis_id": kwargs["analysis_id"],
                "task_id": kwargs.get("task_id")
            }
        )

    def work_failed(self, **kwargs):
        self.queue_call(
            set_failed, {
                "worktype": kwargs["worktype"],
                "analysis_id": kwargs["analysis_id"],
                "task_id": kwargs.get("task_id")
            }
        )

    def task_done(self, **kwargs):
        self.queue_call(
            handle_task_done, {
                "task_id": kwargs["task_id"]
            }
        )

    def task_failed(self, **kwargs):
        self.queue_call(
            set_task_failed, {
                "task_id": kwargs["task_id"]
            }
        )

    def track_new_analyses(self, **kwargs):
        self.queue_call(track_untracked)

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
            log.warning("Incomplete message received.", msg=msg, error=e)
        except TypeError as e:
            log.warning("Incorrect message received.", msg=msg, error=e)

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
