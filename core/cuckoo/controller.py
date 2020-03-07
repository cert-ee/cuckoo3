# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import threading
import traceback

from cuckoo.processing import typehelpers

from . import analysis, db
from .instance import WorkerHandler
from .ipc import UnixSocketServer, ReaderWriter
from .storage import Paths, AnalysisPaths


class _Resources:

    def __init__(self):
        self.workers = None

    def set_worker_handler(self, worker_handler):
        if self.workers:
            raise NotImplementedError(
                "Worker handler cannot be set more than once"
            )

        self.workers = worker_handler

resources = _Resources()

def track_analyses(**kwargs):
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

    analysis.track_analyses(valid_untracked)
    print("Tracked new analyses")
    for tracked in valid_untracked:
        resources.workers.identify(tracked)
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
            resources.workers.pre_analysis(analysis_id)
        else:
            db.set_analysis_state(
                analysis_id, db.AnalysisStates.NO_SELECTED
            )

def set_next_state(**kwargs):
    worktype = kwargs["worktype"]
    work = kwargs.get("work")
    if not work:
        return

    analysis_id = work.get("analysis_id")
    if not analysis_id:
        return

    if worktype == "identification":
        handle_identification_done(analysis_id)

    elif worktype == "pre":
        db.set_analysis_state(analysis_id, db.AnalysisStates.COMPLETED_PRE)

def set_failed(**kwargs):
    worktype = kwargs["worktype"]
    work = kwargs.get("work")
    if not work:
        return

    analysis_id = work.get("analysis_id")

    if worktype == "identification":
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)
    elif worktype == "pre":
        print(f"FATAL ERROR WITH ANALYSIS: {analysis_id}")
        db.set_analysis_state(analysis_id, db.AnalysisStates.FATAL_ERROR)


class Controller(UnixSocketServer):
    
    def __init__(self, controller_sock_path):
        super().__init__(controller_sock_path)

        self.workers_th = None
        self.subject_handler = {
            "tracknew": track_analyses,
            "workdone": set_next_state,
            "workfail": set_failed
        }

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
        except Exception as e:
            traceback.print_exc()
            print(f"Fatal error handling message. Error {e}. Message: {msg}")

    def init(self):
        resources.set_worker_handler(WorkerHandler(self.sock_path))

    def start(self):
        self.workers_th = threading.Thread(
            target=resources.workers.start, args=()
        )
        self.workers_th.start()
        try:
            self.create_socket()
            self.start_accepting()
        except KeyboardInterrupt:
            pass
        finally:
            resources.workers.stop()
            self.stop()
