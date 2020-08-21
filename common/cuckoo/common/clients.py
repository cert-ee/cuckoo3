# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from .ipc import (
    request_unix_socket, message_unix_socket, ResponseTimeoutError, IPCError
)

class ClientError(Exception):
    pass

class ServerResponseError(ClientError):
    pass

class ActionFailedError(ClientError):
    pass


class ResultServerClient:

    @staticmethod
    def add(unix_sock_path, ip, task_id):
        try:
            msg = request_unix_socket(
                unix_sock_path, {"ip": ip, "task_id": task_id, "action": "add"}
            )
        except IPCError as e:
            raise ActionFailedError(
                f"Failure during resultserver add request: {e}"
            )

        if msg.get("status") == "ok":
            return

        raise ActionFailedError(msg.get("reason", ""))

    @staticmethod
    def remove(unix_sock_path, ip, task_id):
        try:
            msg = request_unix_socket(
                unix_sock_path, {
                    "ip": ip,
                    "task_id": task_id,
                    "action": "remove"
                }
            )
        except IPCError as e:
            raise ActionFailedError(
                f"Failure during resultserver remove request: {e}"
            )

        if msg.get("status") == "ok":
            return

        raise ActionFailedError(msg.get("reason", ""))

class MachineryManagerClient:

    def __init__(self, sockpath):
        self.sockpath = sockpath

    def machine_action(self, action, machine_name,
                       wait_response=True, timeout=120):
        msg = {
            "action": action,
            "machine": machine_name
        }

        if not wait_response:
            try:
                return message_unix_socket(self.sockpath, msg)
            except IPCError as e:
                raise ActionFailedError(f"Failed to send machine action: {e}")

        try:
            response =  request_unix_socket(self.sockpath, msg, timeout)
        except ResponseTimeoutError as e:
            raise ActionFailedError(
                f"Response for machine action {action} for "
                f"{machine_name} took too long: {e}"
            )

        if "success" not in response:
            raise ServerResponseError(
                f"Response {repr(response)} does not contain "
                f"mandatory key 'success'"
            )

        success = response["success"]
        reason = response.get("reason", "")
        if not success:
            raise ActionFailedError(
                f"Machine action {action} for {machine_name} failed. "
                f"Reason: {reason}"
            )

    def restore_start(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "restore_start", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def norestore_start(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "norestore_start", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def stop(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "stop", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def acpi_stop(self, machine_name, wait_response=True, timeout=120):
        return self.machine_action(
            "acpi_stop", machine_name, wait_response=wait_response,
            timeout=timeout
        )

    def memory_dump(self, machine_name, wait_response=True, timeout=120):
        raise NotImplementedError()

class TaskRunnerClient:

    @staticmethod
    def start_task(sockpath, kind, task_id, analysis_id, machine,
                    result_ip, result_port):
        try:
            resp = request_unix_socket(sockpath, {
            "action": "starttask", "args": {
                    "kind": kind,
                    "task_id": task_id,
                    "analysis_id": analysis_id,
                    "machine": machine.to_dict(),
                    "result_ip": result_ip,
                    "result_port": result_port
                }
            }, timeout=60)
        except IPCError as e:
            raise ActionFailedError(
                f"Failed to send new task to task runner: {e}"
            )

        if not resp.get("success"):
            raise ActionFailedError(
                f"Task runner could not start task. "
                f"Error: {resp.get('reason')}"
            )

class StateControllerClient:

    @staticmethod
    def notify(sockpath):
        """Send a ping to the state controller at the end of the given sock
        path to ask it to track all untracked analyses. Newly submitted
        analyses will not be tracked until the state controller receives a
        notify message."""
        try:
            message_unix_socket(sockpath, {"subject": "tracknew"})
        except IPCError as e:
            raise ActionFailedError(f"Failed to notify state controller. {e}")

    @staticmethod
    def manual_set_settings(sockpath, analysis_id, settings_dict):
        try:
            message_unix_socket(sockpath, {
                "subject": "manualsetsettings",
                "analysis_id": analysis_id,
                "settings_dict": settings_dict
            })
        except IPCError as e:
            raise ActionFailedError(
                f"Failed to send settings to state controller. {e}"
            )
