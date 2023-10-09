# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import asyncio
import errno
import logging
import os
import socket
import threading
import time

from cuckoo.common.ipc import UnixSocketServer, ReaderWriter, IPCError
from cuckoo.common.log import CuckooGlobalLogger, TaskLogger, exit_error
from cuckoo.common.node import ExistingResultServer
from cuckoo.common.shutdown import register_shutdown, call_registered_shutdowns
from cuckoo.common.startup import init_global_logging
from cuckoo.common.storage import (
    cuckoocwd, TaskPaths, Paths, split_task_id, delete_file
)
from cuckoo.common.utils import bytes_to_human, fds_to_hardlimit

log = CuckooGlobalLogger(__name__)

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

class HeaderMisMatch(CancelResult):
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

        self._servers.add(
            ExistingResultServer(socket_path, listen_ip, listen_port)
        )

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
    "logs": TaskPaths.logfile,
    "memory": TaskPaths.procmem_dump,
    "files": TaskPaths.dropped_file
}

# Prevent malicious clients from using potentially dangerous filenames
# E.g. C API confusion by using null, or using the colon on NTFS (Alternate
# Data Streams);
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
        # Replace any illegal chars with X
        for c in BANNED_PATH_CHARS:
            name = name.replace(c, "X")

    return RESULT_UPLOADABLE[dir_part], dir_part, name

async def copy_to_fd(reader, fd, max_size=None, readsize=16384, header=None):
    if max_size:
        fd = WriteLimiter(fd, max_size)

    try:
        if header:
            try:
                buf = await reader.readexactly(len(header))
            except EOFError:
                raise HeaderMisMatch("EOF before header could be compared")

            if buf != header:
                raise HeaderMisMatch(
                    "Stream header does not match expected header"
                )

            fd.write(buf)
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
    def __init__(self, task_mapping, reader):
        self.task = task_mapping
        self.reader = reader
        self.fd = None

    def close(self):
        if self.fd:
            self.fd.close()

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
        path_helper, dirpart, fname = sanitize_dumppath(
            dir_fname.decode(errors="ignore")
        )

        newfile = repr(f"{dirpart}/{fname}")
        self.task.log.debug("New file upload starting.", newfile=newfile)

        try:
            self.fd = open(path_helper(self.task.task_id, fname), "xb")
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise CancelResult(
                    f"Task {self.task.task_id} file upload {newfile}"
                    f"file overwrite attempt stopped."
                )

            raise CancelResult(f"Unhandled error: {e}")

        try:
            await copy_to_fd(
                self.reader, self.fd, self.max_upload_size, readsize=2048
            )
        except MaxBytesWritten as e:
            raise CancelResult(
                f"Task {self.task.task_id} file upload {dirpart}/{fname!r}"
                f" cancelled. {e}"
            )
        except ConnectionError as e:
            raise CancelResult(
                f"Error during connection of file upload {dirpart}/{fname!r} "
                f"of task {self.task.task_id}. {e}"
            )
        finally:
            self.task.log.debug(
                "File upload ended.", newfile=newfile,
                size=bytes_to_human(self.fd.tell())
            )

class ScreenshotUpload(ProtocolHandler):

    # All screenshots must be jpegs. We check this when accepting a new
    # screenshot upload. This can be circumvented, it is purely meant as a
    # simple check.
    JPEG_HEADER = b"\xff\xd8"

    def init(self):
        # Screenshots must always be jpg (can be lossy compressed) and should
        # never be larger than ~4 mb. Medium/low detail is more than enough.
        self.max_upload_size = 1024 * 1024 * 4

    async def handle(self):
        # The timestamp is an approximation of when the screenshot was taken
        # during the task run. It will be off by the amount of time it takes
        # to start the vm, run the screenshot aux module, etc.
        fname = f"{self.task.ts}.jpg"
        self.task.log.debug("New screenshot upload", newfile=fname)
        upload_path = TaskPaths.screenshot(self.task.task_id, fname)
        try:
            self.fd = open(upload_path, "xb")
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise CancelResult(
                    f"Task {self.task.task_id} screenshot upload {fname}"
                    f"file overwrite attempt stopped."
                )

            raise CancelResult(f"Unhandled error: {e}")

        try:
            await copy_to_fd(
                self.reader, self.fd, self.max_upload_size, readsize=2048,
                header=self.JPEG_HEADER
            )
        except HeaderMisMatch as e:
            delete_file(upload_path)
            raise CancelResult(
                f"Task {self.task.task_id} screenshot upload {fname} "
                f"cancelled. Header mismatch: {e}"
            )
        except MaxBytesWritten as e:
            raise CancelResult(
                f"Task {self.task.task_id} screenshot upload {fname} "
                f"cancelled. {e}"
            )
        except ConnectionError as e:
            raise CancelResult(
                f"Error during connection of screenshot upload {fname} "
                f"of task {self.task.task_id}. {e}"
            )
        finally:
            self.task.log.debug(
                "Screenshot upload ended.", newfile=fname,
                size=bytes_to_human(self.fd.tell())
            )

class _MappedTask:

    def __init__(self, task_id, ip, asyncio_rs):
        self.task_id = task_id
        self.ip = ip
        self._start = time.monotonic()
        self.asyncio_rs = asyncio_rs

        self.log = TaskLogger(__name__, task_id)
        self.asynctasks = set()

    @property
    def ts(self):
        """Get the timestamp in milliseconds since the task was mapped"""
        return int((time.monotonic() - self._start) * 1000)

    async def cancel_running_tasks(self):
        for task in list(self.asynctasks):
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.log.exception(
                    "Unexpected error during asyncio task cancel", error=e
                )

        self.log.close()

    def close(self):
        if not self.asynctasks:
            self.log.close()
            return

        # Start a coroutine which will cancel each still running asyncio
        # task and wait until it is cancelled. Closes the log after that.
        asyncio.run_coroutine_threadsafe(
            self.cancel_running_tasks(), self.asyncio_rs.loop
        )


class _AsyncResultServer:

    protocols = {
        "FILE": FileUpload,
        "SCREENSHOT": ScreenshotUpload
    }

    def __init__(self):
        self._ip_task = {}
        self._mapping_lock = threading.RLock()

        # Initialized when start() is called.
        self.loop = None
        self._server = None

    def map_task_ip(self, task_id, ip):
        with self._mapping_lock:
            if task_id in self._ip_task:
                existing_mapping = self._ip_task[ip]
                raise KeyError(
                    f"IP {ip} is already mapped to task "
                    f"{existing_mapping.task_id}"
                )

            self._ip_task[ip] = _MappedTask(task_id, ip, self)

    def unmap_ip(self, ip):
        with self._mapping_lock:
            taskmapping = self._ip_task.pop(ip, None)
            if not taskmapping:
                return

            taskmapping.close()

    def cancel_all(self):
        with self._mapping_lock:
            for ip in list(self._ip_task):
                self.unmap_ip(ip)

    def get_task_mapping(self, ip):
        with self._mapping_lock:
            task_mapping = self._ip_task.get(ip)
            if not task_mapping:
                raise UnmappedIPError(
                    f"IP {ip} is not mapped to any tasks. Cannot store "
                    f"results."
                )
            return task_mapping

    async def get_protocolhandler(self, reader):
        header = await reader.readline()
        if not header:
            raise CancelResult("No protocol header specified")

        protos = header.decode().split()
        proto_handler = self.protocols.get(protos[0])
        if not proto_handler:
            raise UnsupportedProtocol(f"Unknown protocol: {protos[0]!r}")

        return proto_handler, protos[0]

    async def handle_protocol(self, protocol_instance, writer):
        protocol_instance.init()
        try:
            await protocol_instance.handle()
        except CancelResult as e:
            protocol_instance.task.log.warning(
                "Result for task cancelled.", error=e
            )
        finally:
            protocol_instance.close()
            writer.close()

    async def new_result(self, reader, writer):
        ip, port = writer.get_extra_info("peername")
        try:
            task_mapping = self.get_task_mapping(ip)
        except UnmappedIPError as e:
            log.error("Failed to store new task result", error=e)
            writer.close()
            return

        try:
            protocol_handler, protocol = await self.get_protocolhandler(reader)
        except ConnectionError:
            # Ignore, upload was likely stopped because of end of task.
            return
        except CancelResult as e:
            task_mapping.log.warning(
                "Task result cancelled during initialization.",
                task_id=task_mapping.task_id, error=e
            )
            writer.close()
            return

        handler = protocol_handler(task_mapping, reader)

        def _cleanup_cb(task):
            try:
                exp = task.exception()
                if exp:
                    log.exception(
                        "Unhandled exception during asyncio task",
                        error=exp, exc_info=exp
                    )
            except asyncio.CancelledError:
                pass
            finally:
                handler.close()
                writer.close()
                task_mapping.asynctasks.discard(task)

        async_task = self.loop.create_task(
            self.handle_protocol(handler, writer)
        )
        task_mapping.asynctasks.add(async_task)
        async_task.add_done_callback(_cleanup_cb)

    def start(self, listen_ip, listen_port):
        """Start the asyncresultserver on the given ip:port and handle
        incoming results that are mapped."""
        self.loop = asyncio.get_event_loop()
        routine = asyncio.start_server(
            self.new_result, listen_ip, listen_port
        )

        try:
            self._server = self.loop.run_until_complete(routine)
        except OSError as e:
            exit_error(
                f"Failed to start resultserver on: "
                f"{listen_ip}:{listen_port}. {e}"
            )

        log.info(
            "Started resultserver.", listen_ip=listen_ip,
            listen_port=listen_port
        )

        # Give the loop its own thread so we can accept add/remove requests
        # in the main thread.
        loopth = threading.Thread(target=self.loop.run_forever)
        loopth.daemon = True
        loopth.start()
        return loopth

    def stop(self):
        def _stop_loop():
            self.loop.stop()
            self._server.close()
            self._server.wait_closed()

        if self._server:
            self.loop.call_soon_threadsafe(_stop_loop)


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

    def __init__(self, unix_sock_path, cuckoo_cwd, listen_ip, listen_port,
                 loglevel=logging.DEBUG):
        super().__init__(unix_sock_path)
        self.cuckoocwd = cuckoo_cwd
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.loglevel = loglevel

        self._rs = None

    def init(self):
        cuckoocwd.set(
            self.cuckoocwd.root, analyses_dir=self.cuckoocwd.analyses
        )
        register_shutdown(self.stop)

        init_global_logging(
            self.loglevel, Paths.log("resultserver.log"), use_logqueue=False
        )

        try:
            changed, newmax = fds_to_hardlimit()
            if changed:
                log.info(
                    "Changed maximum file descriptors to hard limit for "
                    "current process",
                    newmax=newmax
                )
        except ResourceWarning as e:
            log.error(
                "Error while increasing maximum file descriptors", error=e
            )
        except OSError as e:
            exit_error(
                f"Failure during increasing of maximum file descriptors: {e}"
            )

        # Initialize here, as we are currently using multiprocessing.Process
        # to start this in a new process. _AsyncResultServer uses an RLock,
        # which cannot be pickled. This causes Process creation to fail.
        self._rs = _AsyncResultServer()

    def _start_all(self):
        try:
            self.create_socket()
        except IPCError as e:
            exit_error(f"Failed to create unix socket: {e}")

        try:
            loopth = self._rs.start(self.listen_ip, self.listen_port)
        except OSError as e:
            exit_error(
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

        log.info("Stopping resultserver..")
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
            log.debug(
                "Failed to send response to action requester.",
                response=response, error=e
            )

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
        except (ValueError, TypeError, OSError):
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
