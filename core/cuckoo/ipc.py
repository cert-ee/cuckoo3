# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import errno
import os
import socket
import json
import select
import time

class IPCError(Exception):
    pass


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

            if not buf and not self.rcvbuf:
                return

            if not buf:
                raise EOFError(f"Last byte is: {repr(self.rcvbuf[:1])}")

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
        except (ValueError, EOFError):
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

class UnixSocketServer:

    def __init__(self, sock_path):
        self.sock_path = sock_path
        self.sock = None
        self.do_run = True
        self.socks_readers = {}

    def create_socket(self, backlog=0):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(self.sock_path)
        except socket.error as e:
            raise IPCError(
                f"Failed to bind to unix socket path {self.sock_path}. "
                f"Error: {e}"
            )

        sock.listen(backlog)
        self.sock = sock

    def stop(self):
        self.do_run = False

    def track(self, sock, reader):
        self.socks_readers[sock] = reader

    def untrack(self, sock):
        try:
            sock.close()
        except socket.error:
            pass

        self.socks_readers.pop(sock, None)

    def start_accepting(self, select_timeout=2):

        while self.do_run:
            incoming, _o, _e = select.select(
                list(self.socks_readers.keys()) + [self.sock], [], [],
                select_timeout
            )

            if not incoming:
                continue

            for sock in incoming:

                # Handle new connection
                if sock == self.sock:
                    clientsock, addr = sock.accept()
                    clientsock.setblocking(0)
                    self.handle_connection(clientsock, addr)
                else:
                    reader = self.socks_readers.get(sock)
                    if not reader:
                        print("NO READER")
                        continue

                    first = True
                    while True:
                        try:
                            msg = reader.get_json_message()
                        except (socket.error, ValueError, EOFError,
                                json.decoder.JSONDecodeError) as e:
                            print(f"Failure reading message: {e}")
                            # Untrack this socket. Clients must follow the
                            # communication rules.
                            self.untrack(sock)
                            break

                        if not msg:
                            if first:
                                print("REMOVING DISCONNECTED SOCKET MAPPING")
                                self.untrack(sock)
                            break

                        first = False
                        self.handle_message(sock, msg)


    def cleanup(self, sig=None, f=None):
        self.do_run = False
        if self.sock:
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
        pass

    def handle_message(self, sock, msg):
        pass

    def __del__(self):
        self.cleanup()


class UnixSockClient:

    def __init__(self, sockpath):
        self.sockpath = sockpath
        self.sock = None
        self.reader = None

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
                err = f"Failed to connect to unix socket: {self.sockpath}. " \
                      f"Error: {e}"
                if maxtries and tries >= tries:
                    raise IPCError(err)

                print(err)
                time.sleep(3)

        self.sock = sock
        self.reader = ReaderWriter(sock)

    def send_json_message(self, mes_dict):
        msg = json.dumps(mes_dict)

        try:
            self.sock.sendall(f"{msg}\n".encode())
        except socket.error as e:
            raise IPCError(
                f"Failed to send message to {self.sockpath}. Error: {e}"
            )

    def recv_json_message(self):
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
    if not os.path.exists(sock_path):
        raise IPCError(f"Unix socket {sock_path} does not exist")

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        sock.connect(sock_path)
    except socket.error as e:
        raise IPCError(f"Could not connect to socket: {sock_path}. Error: {e}")

    sock.sendall(f"{json.dumps(message_dict)}\n".encode())
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
