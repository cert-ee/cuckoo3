# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import requests
import json.decoder
from urllib.parse import urljoin

from .ipc import (
    request_unix_socket, message_unix_socket, ResponseTimeoutError, IPCError
)

class ClientError(Exception):
    pass

class ClientConnectionError(ClientError):
    pass

class ServerResponseError(ClientError):
    pass

class ActionFailedError(ClientError):
    pass

class APIError(ClientError):
    pass

class APIServerError(APIError):
    pass

class APIBadRequestError(APIError):
    pass

class APIResourceConfictError(APIBadRequestError):
    pass

class APIDoesNotExistError(APIError):
    pass

class APIPermissionDenied(APIError):
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
            raise ActionFailedError(
                f"Failed to notify state controller of new analyses. {e}"
            )

    @staticmethod
    def notify_exports(sockpath):
        """Ask the state controller at the end of the given sock path to
        set all analysis ids in cwd/exported to location 'remote'"""
        try:
            message_unix_socket(sockpath, {"subject": "setremote"})
        except IPCError as e:
            raise ActionFailedError(
                f"Failed to notify state controller of exported analyses. {e}"
            )

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

class ImportControllerClient:

    @staticmethod
    def notify(sockpath):
        """Send a ping to the import controller at the end of the given sock
        path to ask it to import all stored importables. Newly submitted
        stored importables will not be tracked until the import controller
        receices a notify message."""
        try:
            message_unix_socket(sockpath, {"subject": "trackimportables"})
        except IPCError as e:
            raise ActionFailedError(f"Failed to notify state controller. {e}")

class APIClient:

    def __init__(self, api_host, api_key):
        self._key = api_key
        self._host = api_host

    def _make_headers(self):
        return {
            "Authorization": f"token {self._key}"
        }

    def _raise_for_status(self, response, endpoint, expected_status=200):
        try:
            resjson = response.json()
            error = resjson.get("error")
            if not error:
                error = resjson.get("detail")
        except json.decoder.JSONDecodeError:
            error = None

        code = response.status_code
        if code >= 500:
            raise APIServerError(
                f"API server error on endpoint: "
                f"{endpoint}.{'' if not error else error}"
            )
        elif code == 400:
            raise APIBadRequestError(
                f"Bad request made to endpoint: "
                f"{endpoint}.{'' if not error else error}"
            )
        elif code == 401:
            raise APIPermissionDenied(
                f"The given api key does not have permission to access "
                f"endpoint: {endpoint}"
            )
        elif code == 404:
            raise APIDoesNotExistError(
                f"Requested resource does not exist. Endpoint {endpoint}"
            )
        elif code == 409:
            raise APIResourceConfictError(
                f"Conflict, resource already exists. "
                f"Endpoint: {endpoint}. {'' if not error else error}"
            )

        raise APIError(
            f"Expected status code: {expected_status}. Got {code} on "
            f"endpoint: {endpoint}.{'' if not error else error}"
        )

    def _do_json_get(self, endpoint, expected_status=200):
        url = urljoin(self._host, endpoint)
        try:
            res = requests.get(url, headers=self._make_headers())
        except requests.exceptions.ConnectionError as e:
            raise ClientConnectionError(
                f"Failed to connect to API endpoint {self._host}. {e}"
            )
        except requests.exceptions.RequestException as e:
            raise ClientError(f"API request failed: {e}")

        if res.status_code != expected_status:
            self._raise_for_status(res, endpoint, expected_status)

        return res.json()

    def _do_json_post(self, endpoint, expected_status=200, **kwargs):
        url = urljoin(self._host, endpoint)
        try:
            res = requests.post(url, headers=self._make_headers(), json=kwargs)
        except requests.exceptions.ConnectionError as e:
            raise ClientConnectionError(
                f"Failed to connect to API endpoint {self._host}. {e}"
            )
        except requests.exceptions.RequestException as e:
            raise ClientError(f"API request failed: {e}")

        if res.status_code != expected_status:
            self._raise_for_status(res, endpoint, expected_status)

        return res.json()

    def analysis(self, analysis_id):
        return self._do_json_get(
            f"/analysis/{analysis_id}", expected_status=200
        )

    def pre(self, analysis_id):
        return self._do_json_get(
            f"/analysis/{analysis_id}/pre", expected_status=200
        )


    def identification(self, analysis_id):
        return self._do_json_get(
            f"/analysis/{analysis_id}/identification", expected_status=200
        )

    def analysis_composite(self, analysis_id, retrieve=[]):
        return self._do_json_post(
            f"/analysis/{analysis_id}/composite", expected_status=200,
            retrieve=retrieve
        )

    def task(self, analysis_id, task_id):
        return self._do_json_get(
            f"/analysis/{analysis_id}/task/{task_id}", expected_status=200
        )

    def task_post(self, analysis_id, task_id):
        return self._do_json_get(
            f"/analysis/{analysis_id}/task/{task_id}/post", expected_status=200
        )

    def task_machine(self, analysis_id, task_id):
        return self._do_json_get(
            f"/analysis/{analysis_id}/task/{task_id}/machine",
            expected_status=200
        )

    def task_composite(self, analysis_id, task_id, retrieve=[]):
        return self._do_json_post(
            f"analysis/{analysis_id}/task/{task_id}/composite",
            expected_status=200, retrieve=retrieve
        )

    def import_analysis(self, zip_fp):
        endpoint = "/import/analysis"
        url = urljoin(self._host, endpoint)
        try:
            res = requests.post(
                url, headers=self._make_headers(), files={"file": zip_fp}
            )
        except requests.exceptions.ConnectionError as e:
            raise ClientConnectionError(
                f"Failed to connect to API endpoint {self._host}. {e}"
            )
        except requests.exceptions.RequestException as e:
            raise ClientError(f"API request failed: {e}")

        if res.status_code != 200:
            self._raise_for_status(res, endpoint, 200)

    def import_notify(self):
        endpoint = "/import/analysis"
        url = urljoin(self._host, endpoint)
        try:
            res = requests.put(url, headers=self._make_headers())
        except requests.exceptions.ConnectionError as e:
            raise ClientConnectionError(
                f"Failed to connect to API endpoint {self._host}. {e}"
            )
        except requests.exceptions.RequestException as e:
            raise ClientError(f"API request failed: {e}")

        if res.status_code != 200:
            self._raise_for_status(res, endpoint, 200)
