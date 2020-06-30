# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import asyncio
import errno
import os
import socket
import sys
import threading

from cuckoo.common.ipc import UnixSocketServer, ReaderWriter, IPCError
from cuckoo.common.storage import cuckoocwd, TaskPaths, split_task_id
from cuckoo.shutdown import register_shutdown, call_registered_shutdowns
from cuckoo.common.utils import bytes_to_human

class CancelResult(Exception):
    pass

class UnsupportedProtocol(CancelResult):
    pass

class UnmappedIPError(CancelResult):
    pass

class MaxBytesWritten(CancelResult):
    pass

class IllegalFilePath(CancelResult):
    pass

class ResultServersNotStartedError(Exception):
    pass

class _ResultServerTracker:
    """Simple wrapper around a set to keep track of existing resultservers and
     retrieve information needed to use them."""

    def __init__(self):
        self._servers = set()

    def add(self, socket_path, listen_ip, listen_port):
        if not os.path.exists(socket_path):
            raise FileNotFoundError(
                f"Socket path does not exist: {socket_path}"
            )

        self._servers.add((socket_path, listen_ip, listen_port))

    def get(self):
        """Retrieve a running resultserver. Returns its unix sock path,
         listen ip, and listen port"""
        if not self._servers:
            raise ResultServersNotStartedError(
                "No resultservers were started and added to the "
                "resultserver tracker."
            )

        return next(iter(self._servers))

# A single instance of __ResultServerTracker should be used to add and retrieve
# running resultservers and information to use them.
servers = _ResultServerTracker()


# Directories in which analysis-related files will be stored; Acts as a
# safelist and mapping to path helper to find the actual path in the CWD
RESULT_UPLOADABLE = {
    "logs": TaskPaths.logfile
}

# Prevent malicious clients from using potentially dangerous filenames
# E.g. C API confusion by using null, or using the colon on NTFS (Alternate
# Data Streams); XXX: just replace illegal chars?
BANNED_PATH_CHARS = "\x00:"


def sanitize_dumppath(path):
    """Validate provided path is allowed to be written to and filename does
    not contain any illegal characters.
    Return a cwd_helper, dirname, and filename"""
    path = path.replace("\\", "/").strip()
    dir_part, name = os.path.split(path)
    if dir_part not in RESULT_UPLOADABLE:
        raise IllegalFilePath(f"Banned path requested in upload: {path!r}")

    if any(c in BANNED_PATH_CHARS for c in path):
        for c in BANNED_PATH_CHARS:
            name = name.replace(c, "X")

    return RESULT_UPLOADABLE[dir_part], dir_part, name

async def copy_to_fd(reader, fd, max_size=None, readsize=16384):
    if max_size:
        fd = WriteLimiter(fd, max_size)

    try:
        while True:
            buf = await reader.read(readsize)
            if buf == b"":
                break

            fd.write(buf)
    finally:
        fd.flush()

class ProtocolHandler(object):
    """Abstract class for protocol handlers used by _AsyncResultServer.
    An implement protocol should be added to _AsyncResultServer.protocols.

    Any state at which an incoming result must be ignored/stopped a
    CancelResult must be raised."""
    def __init__(self, task_id, ip, reader):
        self.task_id = task_id
        self.ip = ip
        self.reader = reader
        self.fd = None

    def close(self):
        if self.fd:
            self.fd.close()
            self.fd = None

    async def handle(self):
        raise NotImplementedError


class WriteLimiter:
    def __init__(self, fp, limit):
        self.fp = fp
        self.remain = limit
        self.limit = limit

    def write(self, buf):
        size = len(buf)
        write = min(size, self.remain)
        if write:
            self.fp.write(buf[:write])
            self.remain -= write

        if size and size != write:
            self.fp.write(b"... (truncated by resultserver)")
            raise MaxBytesWritten(
                f"Max size of {bytes_to_human(self.limit)} reached. "
                f"File truncated."
            )

    def flush(self):
        self.fp.flush()

class FileUpload(ProtocolHandler):
     def init(self):
         self.max_upload_size = 1024 * 1024 * 128 # TODO read from config

     async def handle(self):
         dir_fname = await self.reader.readline()
         path_helper, dirpart, fname = sanitize_dumppath(dir_fname.decode())
         print(
             f"Task {self.task_id} file upload {dirpart}/{fname!r} starting."
         )

         try:
             self.fd = open(path_helper(self.task_id, fname), "xb")
         except OSError as e:
             if e.errno == errno.EEXIST:
                 raise CancelResult(
                     f"Task {self.task_id} file upload {dirpart}/{fname!r} "
                     f"file overwrite attempt stopped."
                 )

             raise CancelResult(f"Unhandled error: {e}")

         try:
             await copy_to_fd(
                 self.reader, self.fd, self.max_upload_size, readsize=2048
             )
         except MaxBytesWritten as e:
             raise CancelResult(
                 f"Task {self.task_id} file upload {dirpart}/{fname!r}"
                 f" cancelled. {e}"
             )
         finally:
             print(
                 f"Task {self.task_id} file upload {dirpart}/{fname!r} "
                 f"finished. Size {bytes_to_human(self.fd.tell())}."
             )

class _AsyncResultServer:

    protocols = {
        "FILE": FileUpload
    }

    def __init__(self):
        self._ip_task_id = {}
        self._mapping_lock = threading.RLock()
        self._ip_asynctask = {}

        # Initialized when start() is called.
        self._loop = None
        self._server = None

    def map_task_ip(self, task_id, ip):
        with self._mapping_lock:
            if task_id in self._ip_task_id:
                raise KeyError(
                    f"IP {ip} is already mapped to task {self._ip_task_id[ip]}"
                )

            self._ip_task_id[ip] = task_id
            self._ip_asynctask[ip] = set()

    def unmap_ip(self, ip):
        with self._mapping_lock:
            self._ip_task_id.pop(ip, None)
            incompleted_tasks = self._ip_asynctask.pop(ip, None)

        if incompleted_tasks:
            self._loop.call_soon_threadsafe(
                self.cancel_asynctasks, incompleted_tasks
            )

    def cancel_all(self):
        with self._mapping_lock:
            for ip in list(self._ip_task_id):
                self.unmap_ip(ip)

    def get_task_id(self, ip):
        with self._mapping_lock:
            task_id = self._ip_task_id.get(ip)
            if not task_id:
                print(self._ip_task_id)
                raise UnmappedIPError(
                    f"IP {ip} is not mapped to any tasks. Cannot store "
                    f"results."
                )
            return task_id

    async def get_protocolhandler(self, reader):
        header = await reader.readline()
        if not header:
            raise CancelResult("No protocol header specified")

        protos = header.decode().split()
        proto_handler = self.protocols.get(protos[0])
        if not proto_handler:
            raise UnsupportedProtocol(f"Unknown protocol: {protos[0]!r}")

        return proto_handler, protos[0]

    async def handle_protocol(self, protocol_instance):
        protocol_instance.init()
        try:
            await protocol_instance.handle()
        except CancelResult as e:
            print(f"Task {protocol_instance.task_id} cancelled: {e}")

    def cancel_asynctasks(self, tasks):
        for task in list(tasks):
            try:
                task.cancel()
            except asyncio.CancelledError:
                print(f"Ok,cancelled: {task}")

    async def new_result(self, reader, writer):
        ip, port = writer.get_extra_info("peername")
        try:
            task_id = self.get_task_id(ip)
        except UnmappedIPError as e:
            print(e)
            return

        try:
            protocol_handler, protocol = await self.get_protocolhandler(reader)
        except CancelResult as e:
            print(
                f"Task {task_id} result cancelled during "
                f"initialization: {e}"
            )
            return

        asynctasks = self._ip_asynctask[ip]
        handler = protocol_handler(task_id, ip, reader)

        def cleanup(task):
            handler.close()
            writer.close()
            asynctasks.discard(task)

        async_task = asyncio.Task(self.handle_protocol(handler))
        async_task.add_done_callback(cleanup)
        asynctasks.add(async_task)

    def start(self, listen_ip, listen_port):
        """Start the asyncresultserver on the given ip:port and handle
        incoming results that are mapped."""
        self._loop = asyncio.get_event_loop()
        routine = asyncio.start_server(
            self.new_result, listen_ip, listen_port, loop=self._loop
        )

        try:
            self._server = self._loop.run_until_complete(routine)
        except OSError as e:
            sys.exit(
                f"Failed to start resultserver on: "
                f"{listen_ip}:{listen_port}. {e}"
            )

        print(f"Started resultserver on: {listen_ip}:{listen_port}")

        # Give the loop its own thread so we can accept add/remove requests
        # in the main thread.
        loopth = threading.Thread(target=self._loop.run_forever)
        loopth.daemon = True
        loopth.start()
        return loopth

    def stop(self):
        def _stop_loop():
            self._loop.stop()
            self._server.close()
            self._server.wait_closed()

        if self._server:
            self._loop.call_soon_threadsafe(_stop_loop)


class _RSResponses:

    @staticmethod
    def success():
        return {
            "status": "ok"
        }

    @staticmethod
    def fail(reason=""):
        return {
            "status": "fail",
            "reason": reason
        }

class ResultServer(UnixSocketServer):

    def __init__(self, unix_sock_path, cuckoo_cwd, listen_ip, listen_port):
        super().__init__(unix_sock_path)
        self.cuckoocwd = cuckoo_cwd
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        self._rs = None
        self._loop = None
        self._server = None

    def init(self):
        cuckoocwd.set(self.cuckoocwd)
        register_shutdown(self.stop)

        # Initialize here, as we are currently using multiprocessing.Process
        # to start this in a new process. _AsyncResultServer uses an RLock,
        # which cannot be pickled. This causes Process creation to fail.
        self._rs = _AsyncResultServer()

    def _start_all(self):
        try:
            self.create_socket()
        except IPCError as e:
            sys.exit(f"Failed to create unix socket: {e}")

        try:
            loopth = self._rs.start(self.listen_ip, self.listen_port)
        except OSError as e:
            sys.exit(
                f"Failed to start resultserver on: "
                f"{self.listen_ip}:{self.listen_port}. {e}"
            )

        # Start accepting requests to add/remove for ip/tasks for which to
        # accept results for.
        self.start_accepting()

        # Wait for event loop thread to stop
        loopth.join(timeout=10)

    def start(self):
        self.init()
        try:
            self._start_all()
        finally:
            call_registered_shutdowns()

    def stop(self):
        if not self.do_run:
            return

        print("Stopping resultserver..")
        super().stop()
        self.untrack_all()
        self._rs.cancel_all()
        self.cleanup()
        self._rs.stop()

    def handle_connection(self, sock, addr):
        self.track(sock, ReaderWriter(sock))

    def respond(self, readerwriter, response):
        try:
            readerwriter.send_json_message(response)
        except socket.error as e:
            print(f"Failed to send response: {e}")

    def handle_message(self, sock, msg):
        ip = msg.get("ip")
        task_id = msg.get("task_id")
        action = msg.get("action")
        readerwriter = self.socks_readers[sock]
        if not ip or not task_id or not action:
            self.respond(
                readerwriter,
                 _RSResponses.fail("Missing ip, task_id, or action")
            )
            return

        try:
            split_task_id(task_id)
        except ValueError as e:
            self.respond(
                readerwriter,
                _RSResponses.fail(f"Invalid task_id: {e}")
            )
            return

        try:
            socket.inet_aton(ip)
        except (ValueError, TypeError):
            self.respond(readerwriter, _RSResponses.fail("Invalid ip"))
            return

        if action == "add":
            try:
                self._rs.map_task_ip(task_id, ip)
                self.respond(readerwriter, _RSResponses.success())
            except KeyError as e:
                self.respond(readerwriter, _RSResponses.fail(str(e)))

        elif action == "remove":
            self._rs.unmap_ip(ip)
            self.respond(readerwriter, _RSResponses.success())
        else:
            self.respond(readerwriter, _RSResponses.fail("Unsupported method"))
