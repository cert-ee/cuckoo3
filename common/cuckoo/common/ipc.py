# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import errno
import os
import socket
import json
import select
import time
import stat

import asyncio

from .log import CuckooGlobalLogger

class IPCError(Exception):
    pass

class NotConnectedError(IPCError):
    pass

class ResponseTimeoutError(IPCError):
    pass

log = CuckooGlobalLogger(__name__)

class ReaderWriter(object):
    # 5 MB JSON blob
    MAX_INFO_BUF = 5 * 1024 * 1024

    def __init__(self, sock):
        self.sock = sock
        self.rcvbuf = b""

    def readline(self):
        while True:
            offset = self.rcvbuf.find(b"\n")
            if offset >= 0:
                l, self.rcvbuf = self.rcvbuf[:offset], self.rcvbuf[offset + 1:]
                return l.decode()

            if len(self.rcvbuf) >= self.MAX_INFO_BUF:
                raise ValueError(
                    f"Received message exceeds {self.MAX_INFO_BUF} bytes"
                )

            try:
                buf = self._read()
            except BlockingIOError as e:
                if e.errno == errno.EWOULDBLOCK:
                    return
                raise

            # Socket was disconnected
            if not buf:
                if self.has_buffered():
                    raise EOFError(
                        f"Last byte must be '\\n'. "
                        f"Actual last byte is: {repr(self.rcvbuf[:1])}"
                    )

                raise NotConnectedError(
                    "Socket disconnected. Cannot receive message."
                )

            self.rcvbuf += buf

    def _read(self, amount=4096):
        return self.sock.recv(amount)

    def clear_buf(self):
        self.rcvbuf = b""

    def has_buffered(self):
        return len(self.rcvbuf) > 0

    def get_json_message(self):
        try:
            message = self.readline()
        except (ValueError, EOFError, NotConnectedError):
            self.clear_buf()
            raise

        if not message:
            return None

        return json.loads(message)

    def send_json_message(self, mes_dict):
        self.sock.sendall(f"{json.dumps(mes_dict)}\n".encode())

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except socket.error:
            pass


_POLL_READREADY = select.POLLIN | select.POLLPRI
_POLL_CLOSABLE = select.POLLHUP | select.POLLRDHUP | select.POLLERR | \
                 select.POLLNVAL
_POLL_READ = _POLL_READREADY | _POLL_CLOSABLE

class UnixSocketServer:

    def __init__(self, sock_path):
        self.sock_path = str(sock_path)
        self.sock = None
        self.do_run = True
        self.socks_readers = {}
        self._fd_socks = {}
        self._poll = None

    def create_socket(self, backlog=0):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            # TODO either here or at usage, check if the path already exists
            # and if we can delete it. EG: pidfile is no longer locked.
            sock.bind(self.sock_path)
        except socket.error as e:
            raise IPCError(
                f"Failed to bind to unix socket path {self.sock_path}. "
                f"Error: {e}"
            )

        # For now, only allow the user running Cuckoo to read from, write
        # to, and execute the created sockets
        os.chmod(self.sock_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        sock.listen(backlog)
        self._poll = select.poll()
        self.sock = sock
        self._fd_socks[sock.fileno()] = sock
        self._poll.register(sock, _POLL_READ)

    def stop(self):
        self.do_run = False

    def track(self, sock, reader):
        """Track when the socket is ready for reading and store the
        passed readerwriter in a socket:rw map"""
        self._fd_socks[sock.fileno()] = sock
        self.socks_readers[sock] = reader
        self._poll.register(sock, _POLL_READ)

    def untrack(self, sock, fd=None):
        if not fd:
            fd = sock.fileno()

        if fd > 0:
            self._poll.unregister(fd)
        try:
            sock.close()
        except socket.error:
            pass

        self.socks_readers.pop(sock, None)
        self._fd_socks.pop(fd, None)

    def untrack_all(self):
        for sock in list(self.socks_readers):
            self.untrack(sock)

    def timeout_action(self):
        """Called after the select timeout expires"""
        pass

    def _read_incoming(self, sock):
        reader = self.socks_readers.get(sock)
        if not reader:
            log.warning(
                "No reader for existing socket connection.",
                sock=sock
            )
            return

        while True:
            try:
                msg = reader.get_json_message()
            except (socket.error, ValueError, EOFError,
                    json.decoder.JSONDecodeError) as e:
                log.warning(
                    "Failed to read message. Disconnecting "
                    "client.", error=e, sock=sock
                )
                # Untrack this socket. Clients must follow the
                # communication rules.
                self.untrack(sock)
                break

            except NotConnectedError:
                self.untrack(sock)
                break

            if not msg:
                break

            self.handle_message(sock, msg)

    def start_accepting(self, timeout=2):
        serv_sock = self.sock
        while self.do_run:
            incoming = self._poll.poll(timeout * 1000)

            self.timeout_action()

            if not incoming:
                continue

            for fd, bitmask in incoming:
                sock = self._fd_socks[fd]

                if bitmask & _POLL_READREADY:
                    if sock is serv_sock:
                        # Handle new connection
                        try:
                            clientsock, addr = sock.accept()
                        except OSError as e:
                            if e.errno == errno.EBADF:
                                continue

                            raise

                        clientsock.setblocking(False)
                        self.handle_connection(clientsock, addr)
                    else:
                        self._read_incoming(sock)

                elif bitmask & _POLL_CLOSABLE:
                    # Untrack and close the socket if anything about the
                    # connection is reset or closed.
                    self.untrack(sock, fd=fd)
                else:
                    raise IPCError(f"Unhandled poll bitmask: {bitmask}")

    def cleanup(self):
        if self.do_run:
            return

        if not self.sock:
            return

        try:
            self.sock.close()
        except socket.error:
            pass

        finally:
            try:
                os.unlink(self.sock_path)
            except FileNotFoundError:
                pass

    def handle_connection(self, sock, addr):
        """Called when a new client connects. Call the track method here
        if the client should be tracked."""
        pass

    def handle_message(self, sock, msg):
        """Called when a new JSON message for a tracked socket arrives."""
        pass


class UnixSockClient:

    def __init__(self, sockpath, blockingreads=True):
        self.blockingreads = blockingreads
        self.sockpath = str(sockpath)
        self.sock = None
        self.reader = None

    def reconnect(self, maxtries=5):
        self.cleanup()
        self.sock = None
        self.reader = None
        self.connect(maxtries)

    def connect(self, maxtries=5):
        if self.sock:
            return

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        tries = 0
        while True:
            if not os.path.exists(self.sockpath):
                time.sleep(1)
                continue

            tries += 1
            try:
                sock.connect(self.sockpath)
                break
            except socket.error as e:
                if maxtries and tries >= tries:
                    raise IPCError(
                        f"Failed to connect to unix socket: {self.sockpath}. "
                        f"Error: {e}"
                    )

                time.sleep(3)

        if not self.blockingreads:
            sock.setblocking(False)

        self.sock = sock
        self.reader = ReaderWriter(sock)

    def send_json_message(self, mes_dict):
        if not self.sock:
            raise NotConnectedError(
                "Not connected to socket. Cannot send message"
            )

        try:
            self.reader.send_json_message(mes_dict)
        except socket.error as e:
            raise IPCError(
                f"Failed to send message to {self.sockpath}. Error: {e}"
            )

    def recv_json_message(self):
        if not self.sock:
            raise NotConnectedError(
                "Not connected to socket. Cannot receive message"
            )

        try:
            return self.reader.get_json_message()
        except socket.error as e:
            raise IPCError(f"Failed to read from socket: {e}")

        except json.decoder.JSONDecodeError as e:
            raise ValueError(f"Received invalid JSON message: {e}")

    def cleanup(self):
        if not self.sock:
            return

        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except socket.error:
            pass

    def __del__(self):
        self.cleanup()


def message_unix_socket(sock_path, message_dict):
    """Send the given message dict to the provided unix socket and
     disconnect"""
    if not os.path.exists(sock_path):
        raise IPCError(f"Unix socket {sock_path} does not exist")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        sock.connect(str(sock_path))
    except socket.error as e:
        raise IPCError(f"Could not connect to socket: {sock_path}. Error: {e}")

    sock.sendall(f"{json.dumps(message_dict)}\n".encode())
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()


def _timeout_read_response(client, timeout):
    waited = 0
    while True:
        resp = client.recv_json_message()
        if resp is not None:
            return resp

        if waited >= timeout:
            raise ResponseTimeoutError(
                f"No response within timeout of {timeout} seconds."
            )

        waited += 1
        time.sleep(1)

def request_unix_socket(sock_path, message_dict, timeout=0):
    """Send the given message dict to the provided unix socket, wait for a
    response, disconnect, and return the response. If the timeout is a higher
    integer than 0, this will be used a maximum amount of seconds
    to wait for the response. If it is reached, a ResponseTimeoutError
    is raised."""
    if not os.path.exists(sock_path):
        raise IPCError(f"Unix socket {sock_path} does not exist")

    if timeout > 0:
        client = UnixSockClient(sock_path, blockingreads=False)
    else:
        client = UnixSockClient(sock_path)

    client.connect(maxtries=1)
    client.send_json_message(message_dict)
    try:
        if timeout > 0:
            return _timeout_read_response(client, timeout)
        else:
            return client.recv_json_message()
    finally:
        client.cleanup()


async def a_request_unix_socket(sock_path, message_dict):
    """Asynchronously send the given message to the given unix socket and wait
     for a response."""
    try:
        reader, writer = await asyncio.open_unix_connection(str(sock_path))
    except FileNotFoundError:
        raise IPCError(f"Unix socket {sock_path} does not exist")

    try:
        writer.write(f"{json.dumps(message_dict)}\n".encode())
        await writer.drain()
    except OSError as e:
        raise IPCError(
            f"Failed to send message to socket: {sock_path}. Error: {e}"
        )

    try:
        data = await reader.readuntil(separator=b"\n")
        writer.close()
    except OSError as e:
        raise IPCError(
            f"Failed to read message from socket: {sock_path}. Error: {e}"
        )
    except EOFError as e:
        raise IPCError(
            f"Unexpected end of message from socket: {sock_path}. Error: {e}"
        )

    return json.loads(data.decode())
