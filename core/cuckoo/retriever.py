# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import queue
import socket
import threading
import time

from cuckoo.common import shutdown
from cuckoo.common.clients import ClientError
from cuckoo.common.importing import unpack_noderesult, AnalysisImportError
from cuckoo.common.ipc import UnixSocketServer, ReaderWriter, IPCError
from cuckoo.common.log import CuckooGlobalLogger, exit_error
from cuckoo.common.startup import init_global_logging
from cuckoo.common.storage import (
    TaskPaths, Paths, split_task_id, cuckoocwd, delete_file
)

log = CuckooGlobalLogger(__name__)

class DownloadWorkException(Exception):
    pass

def _make_response(success=True, error=None):
    msg = {"success": success}
    if error:
        msg["error"] = error

    return msg

class _DownloadWork:

    def __init__(self, task_id, node, readerwriter, closer_func):
        self.task_id = task_id
        self.node = node
        self.readerwriter = readerwriter
        self._closer_func = closer_func

    def download_result(self):
        zip_path = TaskPaths.zipped_results(self.task_id)

        # Already downloaded, return
        if zip_path.exists():
            return

        try:
            self.node.download_result(self.task_id, zip_path)
        except ClientError as e:
            log.warning(
                "Error during result downloading", task_id=self.task_id,
                error=e
            )
            raise DownloadWorkException(e)

    def unpack_result(self):
        zip_path = TaskPaths.zipped_results(self.task_id)
        try:
            unpack_noderesult(zip_path, self.task_id)
        except AnalysisImportError as e:
            log.warning(
                "Error during result unpacking", task_id=self.task_id,
                error=e
            )
            raise DownloadWorkException(e)

        delete_file(zip_path)

    def send_response(self, msgdict):
        try:
            self.readerwriter.send_json_message(msgdict)
        except socket.error as e:
            log.warning(
                "Failed to send message to download requester",
                task_id=self.task_id, error=e
            )

    def close(self):
        self._closer_func(self.readerwriter)

class _Stopwatch:

    def __init__(self):
        self._start = None

    def start(self):
        self._start = time.monotonic()

    def stop(self):
        if not self._start:
            raise ValueError("Stopwatch never started")

        return time.monotonic() - self._start

class _RetrieveWorker(threading.Thread):

    def __init__(self, workqueue):
        super().__init__()

        self.workqueue = workqueue
        self._do_run = True

    def stop(self):
        self._do_run = False

    def run(self):
        while self._do_run:
            try:
                work = self.workqueue.get(timeout=1)
            except queue.Empty:
                continue

            log.debug(
                "Starting retrieving work", task_id=work.task_id,
                node=work.node.name
            )

            s = _Stopwatch()
            s.start()

            try:
                log.debug("Starting download", task_id=work.task_id)
                try:
                    work.download_result()
                except DownloadWorkException as e:
                    work.send_response(
                        _make_response(success=False, error=str(e))
                    )
                    continue

                log.debug(
                    "Finished download", task_id=work.task_id, took=s.stop()
                )

                s.start()
                log.debug("Starting unpack", task_id=work.task_id)
                try:
                    work.unpack_result()
                except DownloadWorkException as e:
                    work.send_response(
                        _make_response(success=False, error=str(e))
                    )
                    continue

                log.debug(
                    "Finished unpack", task_id=work.task_id, took=s.stop()
                )

                work.send_response(_make_response(success=True))
            finally:
                work.close()

            log.debug(
                "Finished retrieving work", task_id=work.task_id,
                node=work.node.name
            )


class ResultRetriever(UnixSocketServer):

    NUM_WORKERS = 4

    def __init__(self, manager_sock_path, cuckoocwd, loglevel):
        super().__init__(manager_sock_path)
        self.cuckoocwd = cuckoocwd
        self.loglevel = loglevel
        self.workers = []
        self.responses = None
        self.workqueue = None
        self.closable_readers = None
        self.nodes = {}

    def add_node(self, name, nodeclient):
        self.nodes[name] = nodeclient

    def init(self):
        cuckoocwd.set(
            self.cuckoocwd.root, analyses_dir=self.cuckoocwd.analyses
        )
        shutdown.register_shutdown(self.stop)
        init_global_logging(
            self.loglevel, Paths.log("retriever.log"), use_logqueue=False
        )

        self.responses = queue.Queue()
        self.workqueue = queue.Queue()
        self.closable_readers = queue.Queue()

    def _start_all(self):
        try:
            self.create_socket()
        except IPCError as e:
            exit_error(f"Failed to create unix socket: {e}")

        for _ in range(self.NUM_WORKERS):
            worker = _RetrieveWorker(self.workqueue)
            worker.daemon = True
            self.workers.append(worker)
            worker.start()

        self.start_accepting(select_timeout=1)

        for worker in self.workers:
            log.debug("Waiting for retriever worker to stop")
            worker.join(timeout=20)

    def start(self):
        self.init()
        try:
            self._start_all()
        finally:
            shutdown.call_registered_shutdowns()

    def stop(self):
        if not self.do_run:
            return

        super().stop()

        log.info("Stopping result retriever")
        for worker in self.workers:
            worker.stop()

        self.cleanup()

    def add_closable_reader(self, readerwriter):
        self.closable_readers.put(readerwriter)

    def handle_connection(self, sock, addr):
        self.track(sock, ReaderWriter(sock))

    def queue_response(self, readerwriter, response, close=False):
        self.responses.put((readerwriter, response, close))

    def timeout_action(self):
        while not self.responses.empty():
            try:
                readerwriter, response, close = self.responses.get(block=False)
            except queue.Empty:
                break

            try:
                readerwriter.send_json_message(response)
            except socket.error as e:
                log.debug("Failed to send response.", error=e)
                self.untrack(readerwriter.sock)
                continue

            if close:
                self.untrack(readerwriter.sock)

        while not self.closable_readers.empty():
            try:
                readerwriter = self.responses.get(block=False)
            except queue.Empty:
                break

            self.untrack(readerwriter.sock)

    def handle_message(self, sock, msg):
        log.debug("New message", msg=msg)
        readerwriter = self.socks_readers[sock]
        try:
            task_id = msg["task_id"]
            node = msg["node"]
        except KeyError as e:
            self.queue_response(
                readerwriter, _make_response(
                    success=False, error=f"Missing required key: {e}"
                ), close=True
            )
            return

        try:
            task_id = str(task_id)
            split_task_id(task_id)
        except (ValueError, TypeError):
            self.queue_response(
                readerwriter, _make_response(
                    success=False, error="Invalid task_id"
                ), close=True
            )
            return

        try:
            nodeclient = self.nodes[node]
        except KeyError:
            self.queue_response(
                readerwriter, _make_response(
                    success=False, error=f"Unknown node: {node}"
                ), close=True
            )
            return

        self.workqueue.put(
            _DownloadWork(
                task_id, nodeclient, readerwriter, self.add_closable_reader
            )
        )
