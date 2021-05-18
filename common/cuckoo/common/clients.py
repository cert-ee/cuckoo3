# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os.path

import aiohttp
import asyncio
import requests
import json.decoder
from urllib.parse import urljoin

from aiohttp_sse_client import client as sse_client
from aiohttp.client_exceptions import ClientError as aiohttpClientError
from aiohttp import ClientSession, ClientTimeout

from .ipc import (
    request_unix_socket, message_unix_socket, ResponseTimeoutError, IPCError,
    a_request_unix_socket
)

from .machines import read_machines_dump_dict, MachineListError

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
            response = request_unix_socket(self.sockpath, msg, timeout)
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
                    resultserver):
        try:
            resp = request_unix_socket(sockpath, {
            "action": "starttask", "args": {
                    "kind": kind,
                    "task_id": task_id,
                    "analysis_id": analysis_id,
                    "machine": machine.to_dict(),
                    "resultserver": resultserver.to_dict()
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

class _Responsectx:

    __slots__ = ("status_code", "json")

    def __init__(self, status_code, json_body):
        self.status_code = status_code
        self.json = json_body or {}

def _response_ctx(response):
    try:
        r_json = response.json()
    except json.JSONDecodeError:
        r_json = None

    return _Responsectx(response.status_code, r_json)

async def _aiohttp_response_ctx(response):
    try:
        print("RES CTX")
        r_json = await response.json()
    except (json.JSONDecodeError, aiohttp.client_exceptions.ClientError):
        print("AAAAAA")
        r_json = None

    return _Responsectx(response.status, r_json)

def _raise_for_status(responsectx, endpoint, expected_status=200):
    error = responsectx.json.get("error") or responsectx.json.get("detail")
    code = responsectx.status_code
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
            f"Requested resource does not exist. Endpoint {endpoint}. "
            f"{'' if not error else error}"
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

class APIClient:

    def __init__(self, api_host, api_key):
        self._key = api_key
        self._host = api_host

    def _make_headers(self):
        return {
            "Authorization": f"token {self._key}"
        }

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
            _raise_for_status(_response_ctx(res), endpoint, expected_status)

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
            _raise_for_status(_response_ctx(res), endpoint, expected_status)

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
            _raise_for_status(_response_ctx(res), endpoint, 200)

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
            _raise_for_status(_response_ctx(res), endpoint, 200)

class NodeAPIClient:

    def __init__(self, api_url, api_key, node_name=None):
        self.api_url = api_url
        self._api_key = api_key
        self.name = node_name

    @property
    def event_endpoint(self):
        return urljoin(self.api_url, "events")

    def get_headers(self):
        return {
            "Authorization": f"token {self._api_key}"
        }

    def ping(self):
        api = urljoin(self.api_url, "ping")
        try:
            res = requests.get(api, timeout=5)
        except requests.exceptions.RequestException as e:
            raise ClientError(f"Node API ping failed. {e}")

        if res.status_code != 200:
            _raise_for_status(_response_ctx(res), api, 200)

    def machine_list(self):
        api = urljoin(self.api_url, f"machines")
        try:
            res = requests.get(api, timeout=5)
        except requests.exceptions.RequestException as e:
            raise ClientError(f"Retrieving machine list failed. {e}")

        if res.status_code != 200:
            _raise_for_status(_response_ctx(res), api, 200)

        try:
            return read_machines_dump_dict(res.json())
        except MachineListError as e:
            raise ClientError(f"Failed to read machine list: {e}")

    def download_result(self, task_id, file_path, chunk_size=256*1024):
        if os.path.exists(file_path):
            raise ClientError(f"Path already exists: {file_path}")

        api = urljoin(self.api_url, f"task/{task_id}")

        try:
            with requests.get(api, stream=True) as r:
                if r.status_code != 200:
                    _raise_for_status(_response_ctx(r), api, 200)

                with open(file_path, "wb") as fp:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        fp.write(chunk)
        except requests.exceptions.RequestException as e:
            raise ClientError(f"Error during result download. {e}")

    async def upload_taskwork(self, zip_path):
        if not os.path.exists(zip_path):
            raise ClientError(f"Zip path does not exist: {zip_path}")

        api = urljoin(self.api_url, "uploadwork")

        try:
            async with aiohttp.ClientSession() as ses:
                with open(zip_path, "rb") as fp:
                    res = await ses.post(api, data={"file": fp})
        except aiohttpClientError as e:
            raise ClientError(f"Error during work upload. {e}")

        if res.status != 200:
            _raise_for_status(await _aiohttp_response_ctx(res), api, 200)

    async def start_task(self, task_id, machine_name):
        api = urljoin(self.api_url, f"task/{task_id}/start")

        async with aiohttp.ClientSession(timeout=ClientTimeout(sock_read=1)) as ses:
            try:
                res = await ses.post(api, json={"machine_name": machine_name})
            except aiohttp.client_exceptions.ClientError as e:
                raise ClientError(f"Error during task start request. {e}")

        if res.status != 200:
            _raise_for_status(await _aiohttp_response_ctx(res), api, 200)

class NodeEventReader:

    def __init__(self, nodeapi_client, message_cb, read_end_cb,
                 connerr_cb=None, conn_cb=None):
        self.client = nodeapi_client
        self._connerr_cb = connerr_cb
        self._conn_cb = conn_cb
        self._message_cb = message_cb
        self._readend_cb = read_end_cb
        self._evsource = None
        self._ses = None
        self.last_id = 0
        self.stopped = False

    @property
    def opened(self):
        return self._evsource.ready_state == sse_client.READY_STATE_OPEN

    async def close(self):
        if self._evsource.ready_state != sse_client.READY_STATE_CLOSED:
            await self._evsource.close()
            await self._ses.close()

    async def stop_reading(self):
        self.stopped = True
        await self.close()

    async def open(self):
        ses = ClientSession(timeout=ClientTimeout(sock_read=0))
        headers = self.client.get_headers()
        if self.last_id:
            headers["Last-Event-Id"] = str(self.last_id)

        evsource = sse_client.EventSource(
            self.client.event_endpoint, session=ses, headers=headers,
        )
        try:
            await evsource.connect(retry=0)
            self._ses = ses
            self._evsource = evsource
            if self._conn_cb:
                self._conn_cb()
        except (aiohttpClientError, ConnectionError) as e:
            await ses.close()
            raise ClientError(
                "Failed to connect to event source:"
                f" {self.client.event_endpoint}. {e}"
            )

    async def read_stream(self):
        if not self._evsource:
            raise ClientError(f"No opened event source")

        evsource = self._evsource
        try:
            async for event in evsource:
                if evsource.ready_state != sse_client.READY_STATE_OPEN:
                    break

                self.last_id = event.last_event_id
                try:
                    await self._message_cb(json.loads(event.data))
                except (TypeError, json.JSONDecodeError):
                    # Ignore invalid message. All messages must be
                    # json.
                    continue

        except (ConnectionError, aiohttpClientError, ValueError,
                asyncio.TimeoutError) as e:
            if self._connerr_cb:
                self._connerr_cb(e)
        finally:
            if evsource.ready_state != sse_client.READY_STATE_CLOSED:
                await self.close()

            await self._readend_cb()

class ResultRetrieverClient:

    @staticmethod
    async def retrieve_result(sock_path, task_id, node_name):
        try:
            response = await a_request_unix_socket(
                sock_path, {"task_id": task_id, "node": node_name}
            )
        except IPCError as e:
            raise ClientError(f"Error in result retriever communication: {e}")

        if not response.get("success"):
            raise ActionFailedError(
                f"Error during result retrieval: {response.get('error')}"
            )
