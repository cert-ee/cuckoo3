# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import queue
import threading

from cuckoo.common import db, analyses, task
from cuckoo.common.submit import SettingsMaker, SubmissionError
from cuckoo.common.errors import ErrorTracker
from cuckoo.common.ipc import UnixSocketServer, ReaderWriter
from cuckoo.common.log import CuckooGlobalLogger, AnalysisLogger, TaskLogger
from cuckoo.common.storage import Paths, AnalysisPaths, TaskPaths
from cuckoo.common.strictcontainer import (
    Analysis, Task, Identification, Pre, Settings
)

from . import started
from .scheduler import task_queue

log = CuckooGlobalLogger(__name__)

_tracking_lock = threading.Lock()

class StateControllerError(Exception):
    pass

def track_untracked(worktracker):
    with _tracking_lock:
        analysis_ids = os.listdir(Paths.untracked())
        if not analysis_ids:
            return

        tracked = analyses.track_analyses(analysis_ids)
        log.info("Tracked new analyses.", amount=len(tracked))

        # Queue the newly tracked analyses for identification.
        for analysis_id in tracked:
            started.processing_handler.identify(analysis_id)

        # Remove all analysis id files from the untracked dir.
        for analysis_id in analysis_ids:
            os.unlink(Paths.untracked(analysis_id))

def handle_identification_done(worktracker):
    analysis = worktracker.analysis

    if analysis.settings.manual:
        db.set_analysis_state(
            worktracker.analysis_id, analyses.States.WAITING_MANUAL
        )
    else:
        ident_path = AnalysisPaths.identjson(worktracker.analysis_id)
        if not os.path.isfile(ident_path):
            worktracker.log.error(
                "Failed to read identification stage file",
                error="File does not exist", filepath=ident_path
            )
            worktracker.errtracker.fatal_error(
                "Failed to read identification stage file. File does not exist"
            )
            db.set_analysis_state(
                worktracker.analysis_id, analyses.States.FATAL_ERROR
            )
            return

        ident = Identification.from_file(ident_path)

        if ident.selected:
            newstate = analyses.States.PENDING_PRE
            worktracker.log.debug(
                "Updating analysis state.", newstate=newstate
            )
            db.set_analysis_state(worktracker.analysis_id, newstate)
            started.processing_handler.pre_analysis(worktracker.analysis_id)
        else:
            newstate = analyses.States.NO_SELECTED
            worktracker.log.debug(
                "Updating analysis state.", newstate=newstate
            )
            db.set_analysis_state(worktracker.analysis_id, newstate)

def handle_pre_done(worktracker):
    analysis = worktracker.analysis

    # We currently only use the identified platforms and tags if the user
    # did not supply either. TODO improve this and move logic to location
    # where the analysis json is already being stored. TODO tags will be per
    # platform/analysis machine. Combine tags when tasks are created
    if not analysis.settings.manual and not analysis.settings.machines:
        ident_path = AnalysisPaths.identjson(worktracker.analysis_id)
        if not os.path.isfile(ident_path):
            worktracker.log.error(
                "Failed to read identified platforms",
                error="Identification processing stage file does not exist.",
                filepath=ident_path
            )
            worktracker.errtracker.fatal_error(
                "Identification processing stage file does not exist."
            )
            db.set_analysis_state(
                worktracker.analysis_id, analyses.States.FATAL_ERROR
            )
            return

        ident = Identification.from_file(ident_path)
        analyses.merge_settings_ident(analysis, ident)

    # Write the final target to the analysis.json
    pre_path = AnalysisPaths.prejson(worktracker.analysis_id)
    if not os.path.isfile(pre_path):
        worktracker.log.error(
            "Failed to read final target",
            error="Pre processing stage file does not exist.",
            filepath=pre_path
        )
        worktracker.errtracker.fatal_error(
            "Pre processing stage file does not exist."
        )
        db.set_analysis_state(
            worktracker.analysis_id, analyses.States.FATAL_ERROR
        )
        return

    pre = Pre.from_file(pre_path)
    analyses.set_final_target(analysis, pre.target)

    # Write to disk here because the target will be read by the task runner.
    # the task can start as soon as it is queued.
    analysis.to_file_safe(
        AnalysisPaths.analysisjson(worktracker.analysis_id)
    )

    worktracker.log.debug("Creating tasks for analysis.")
    try:
        tasks, resource_errs = task.create_all(analysis)
    except task.TaskCreationError as e:
        worktracker.log.error(
            "Failed to create tasks for analysis", error=e
        )
        worktracker.errtracker.fatal_error(
            f"Failed to create tasks for analysis. {e}"
        )
        for err in e.reasons:
            worktracker.errtracker.add_error(err)
            worktracker.log.warning("Task creation failed.", error=err)

        db.set_analysis_state(
            worktracker.analysis_id, analyses.States.FATAL_ERROR
        )
        return

    for err in resource_errs:
        worktracker.errtracker.add_error(err)
        worktracker.log.warning("Task creation failed.", error=err)

    db.set_analysis_state(
        worktracker.analysis_id, analyses.States.COMPLETED_PRE
    )
    task_queue.queue_many(tasks)
    started.scheduler.newtask()

def handle_manual_done(worktracker, settings_dict):
    s_maker = SettingsMaker()
    # We overwrite all settings, but want to retain the 'manual' setting
    # to be able to recognize it was used after this step.
    s_maker.set_manual(True)

    try:
        s_maker.set_priority(settings_dict.get("priority"))
        s_maker.set_timeout(settings_dict.get("timeout"))
        s_maker.set_platforms_list(settings_dict.get("platforms", []))
        s_maker.set_extraction_path(settings_dict.get("extrpath"))
        settings = s_maker.make_settings()
    except SubmissionError as e:
        worktracker.log.error(
            "Failed to update settings for manual state analysis",
            error=e, analysis_id=worktracker.analysis_id
        )
        return

    analyses.overwrite_settings(worktracker.analysis, settings)

    # Write the new settings to the analysis file
    worktracker.analysis.to_file_safe(
        AnalysisPaths.analysisjson(worktracker.analysis_id)
    )

    # Update the analysis to the new pending pre state and queue it for
    # pre analysis processing.
    db.set_analysis_state(worktracker.analysis_id, analyses.States.PENDING_PRE)
    started.processing_handler.pre_analysis(worktracker.analysis_id)

def set_next_state(worktracker, worktype):
    if worktype == "identification":
        analyses.merge_processing_errors(worktracker.analysis)
        handle_identification_done(worktracker)

    elif worktype == "pre":
        analyses.merge_processing_errors(worktracker.analysis)
        handle_pre_done(worktracker)

    elif worktype == "post":
        worktracker.log.info("Setting task to reported.")
        task.merge_processing_errors(worktracker.task)
        task.set_db_state(worktracker.task.id, task.States.REPORTED)

    else:
        raise ValueError(
            f"Unknown work type {worktype} for analysis:"
            f" {worktracker.analysis_id}"
        )

def set_failed(worktracker, worktype):
    if worktype == "identification":
        worktracker.log.error("Analysis identification stage failed")
        analyses.merge_processing_errors(worktracker.analysis)
        db.set_analysis_state(
            worktracker.analysis_id, analyses.States.FATAL_ERROR
        )

    elif worktype == "pre":
        worktracker.log.error("Analysis pre stage failed")
        analyses.merge_processing_errors(worktracker.analysis)
        db.set_analysis_state(
            worktracker.analysis_id, analyses.States.FATAL_ERROR
        )

    elif worktype == "post":
        worktracker.log.error("Task post stage failed")
        task.merge_processing_errors(worktracker.task)
        task.set_db_state(worktracker.task.id, task.States.FATAL_ERROR)

    else:
        raise ValueError(
            f"Unknown work type '{worktype}' for analysis:"
            f" {worktracker.analysis_id}"
        )

def handle_task_done(worktracker):
    started.scheduler.task_ended(worktracker.task_id)
    task.merge_run_errors(worktracker.task)

    worktracker.log.debug("Queueing task for post analysis processing.")
    task.set_db_state(worktracker.task_id, task.States.PENDING_POST)
    started.processing_handler.post_analysis(
        worktracker.analysis_id, worktracker.task_id
    )

def set_task_failed(worktracker):
    worktracker.log.info("Setting task to state failed")
    started.scheduler.task_ended(worktracker.task_id)
    task.merge_run_errors(worktracker.task)
    task.set_db_state(worktracker.task_id, task.States.FATAL_ERROR)

def set_task_running(worktracker):
    worktracker.log.debug("Setting task to state running")
    task.set_db_state(worktracker.task_id, task.States.RUNNING)

class _WorkTracker:

    def __init__(self, func,  **kwargs):
        self._func = func
        self.analysis_id = kwargs.pop("analysis_id", None)
        self.task_id = kwargs.pop("task_id", None)

        self._func_kwargs = kwargs

        self.analysis = None
        self.task = None
        self.log = None

        self.errtracker = ErrorTracker()
        self._load_strictdicts()
        self._make_logger()

    def _make_logger(self):
        if self.task_id:
            self.log = TaskLogger(__name__, self.task_id)
        elif self.analysis_id:
            self.log = AnalysisLogger(__name__, self.analysis_id)
        else:
            self.log = log

    def _load_strictdicts(self):
        if self.analysis_id:
            if not analyses.exists(self.analysis_id):
                raise StateControllerError(
                    f"Analysis {self.analysis_id} does not exist."
                )

            self.analysis = Analysis.from_file(
                AnalysisPaths.analysisjson(self.analysis_id)
            )
        if self.task_id:
            if not task.exists(self.task_id):
                raise StateControllerError(
                    f"Task {self.task_id} does not exist."
                )
            self.task = Task.from_file(TaskPaths.taskjson(self.task_id))


    def run_work(self):
        self._func(self, **self._func_kwargs)

    def close(self):
        self.log.close()
        if self.errtracker.has_errors():
            errors_container = self.errtracker.to_container()
            if self.task_id:
                task.merge_errors(self.task, errors_container)
            elif self.analysis_id:
                analyses.merge_errors(
                    self.analysis, errors_container
                )

        if self.analysis and self.analysis.was_updated:
            self.analysis.to_file_safe(
                AnalysisPaths.analysisjson(self.analysis_id)
            )
        elif self.task and self.task.was_updated:
            self.task.to_file_safe(TaskPaths.taskjson(self.task_id))


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
                worktracker.log.exception(
                    "Failed to run handler function",
                    function=worktracker._func, args=worktracker._func_kwargs,
                    error=e
                )
            finally:
                worktracker.close()


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
            "taskrunfailed": self.task_failed,
            "manualsetsettings": self.manual_set_settings
        }

    def queue_call(self, func, kwargsdict={}):
        if not isinstance(kwargsdict, dict):
            raise TypeError(
                f"Kwargs dict must be a dict. Got: {type(kwargsdict)}"
            )

        self.work_queue.put(_WorkTracker(func, **kwargsdict))

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
                "analysis_id": kwargs["analysis_id"],
                "task_id": kwargs["task_id"]
            }
        )

    def task_running(self, **kwargs):
        self.queue_call(
            set_task_running, {
                "task_id": kwargs["task_id"]
            }
        )

    def task_failed(self, **kwargs):
        self.queue_call(
            set_task_failed, {
                "analysis_id": kwargs["analysis_id"],
                "task_id": kwargs["task_id"]
            }
        )

    def manual_set_settings(self, **kwargs):
        self.queue_call(
            handle_manual_done, {
                "analysis_id": kwargs["analysis_id"],
                "settings_dict": kwargs["settings_dict"]
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
            log.warning("Incomplete message received.", msg=repr(msg), error=e)
        except TypeError as e:
            log.warning("Incorrect message received.", msg=repr(msg), error=e)
        except StateControllerError as e:
            log.error("Error while handling message", error=e)
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
