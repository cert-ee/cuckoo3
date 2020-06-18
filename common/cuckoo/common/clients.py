# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from .ipc import request_unix_socket

class ResultServerClient:

    @staticmethod
    def add(unix_sock_path, ip, task_id):
        msg = request_unix_socket(
            unix_sock_path, {"ip": ip, "task_id": task_id, "action": "add"}
        )
        if msg.get("status") == "ok":
            return True, ""

        return False, msg.get("reason", "")

    @staticmethod
    def remove(unix_sock_path, ip, task_id):
        msg = request_unix_socket(
            unix_sock_path, {"ip": ip, "task_id": task_id, "action": "remove"}
        )
        if msg.get("status") == "ok":
            return True, ""

        return False, msg.get("reason", "")
