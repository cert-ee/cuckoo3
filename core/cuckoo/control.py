# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import queue
import threading
import traceback

from cuckoo.processing import typehelpers

from . import analyses, db, started, task
from cuckoo.common.ipc import UnixSocketServer, ReaderWriter
from cuckoo.common.storage import Paths, AnalysisPaths

def track_untracked():
    analysis_ids = os.listdir(Paths.untracked())
    if not analysis_ids:
        return

    valid_untracked = []
    for untracked_id in analysis_ids:
        untracked_path = Paths.analysis(untracked_id)
        if not os.path.isdir(untracked_path):
            print(
                f"Invalid analysis id, analysis dir {untracked_path} "
                f"does not exist"
            )
            continue

        valid_untracked.append(untracked_id)

    analyses.track_analyses(valid_untracked)
    print("Tracked new analyses")
    for tracked in valid_untracked:
        started.processing_handler.identify(tracked)
        os.unlink(Paths.untracked(tracked))


def handle_identification_done(analysis_id):
    analysis = typehelpers.Analysis.from_file(
        AnalysisPaths.analysisjson(analysis_id)
    )
    if analysis.settings.manual:
        db.set_analysis_state(
            analysis_id, db.AnalysisStates.WAITING_MANUAL
        )
    else:
        ident = typehelpers.Identification.from_file(
            AnalysisPaths.identjson(analysis_id)
        )

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
    analysis = typehelpers.Analysis.from_file(
        AnalysisPaths.analysisjson(analysis_id)
    )

    # We currently only use the identified platforms and tags if the user
    # did not supply either. TODO improve this and move logic to location
    # where the analysis json is already being stored.
    if not analysis.settings.platforms and not analysis.settings.machine_tags:
        ident = typehelpers.Identification.from_file(
            AnalysisPaths.identjson(analysis_id)
        )

        analyses.update_settings(
            analysis, platforms=ident.target.platforms,
            machine_tags=ident.target.machine_tags
        )
        analysis.to_file(AnalysisPaths.analysisjson(analysis_id))

    print(f"Creating tasks for {analysis_id}")
    try:
        task.create_all(analysis)
    except task.TaskCreationError as e:
        print(
            f"Fatal error while creating tasks for analysis: {analysis_id}. "
            f"Error: {e}"
        )
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)
        return

    db.set_analysis_state(analysis_id, db.AnalysisStates.COMPLETED_PRE)

def set_next_state(worktype, analysis_id, task_id=None):
    if worktype == "identification":
        handle_identification_done(analysis_id)

    elif worktype == "pre":
        handle_pre_done(analysis_id)

def set_failed(worktype, analysis_id, task_id=None):
    print(f"Fatal error with analysis: {analysis_id}")
    if worktype == "identification":
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)

    elif worktype == "pre":
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)

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
                traceback.print_exc()
                print(
                    f"Failed to run function: {func} with args: {kwargs}: {e}"
                )

    def stop(self):
        self.do_run = False


class StateController(UnixSocketServer):

    NUM_STATE_CONTROLLER_WORKERS = 2
    
    def __init__(self, controller_sock_path):
        super().__init__(controller_sock_path)

        self.workers = []
        self.work_queue = queue.Queue()
        self.subject_handler = {
            "tracknew": self.track_new_analyses,
            "workdone": self.work_done,
            "workfail": self.work_failed
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
            traceback.print_exc()
            print(f"Incomplete message. Error {e}. Message: {msg}")

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
