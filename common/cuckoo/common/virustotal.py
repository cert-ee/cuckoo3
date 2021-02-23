# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import time
from pathlib import Path

import aiohttp
import vt
import vt.error

class VirustotalError(Exception):
    pass

_vt_api_key = ""

MAX_VT_FILE_SIZE = 32 * 1024 * 1024

def set_api_key(vt_api_key):
    global _vt_api_key
    _vt_api_key = vt_api_key

def _make_results(avs, stats):
    return {
        "avs": avs,
        "stats": stats
    }

def _do_info_request(client, request_str):
    try:
        return client.get_object(request_str)
    except aiohttp.ClientError as e:
        raise VirustotalError(f"Virustotal connection error: {e}")
    except vt.error.APIError as e:
        if e.code == "NotFoundError":
            return None
        elif e.code == "BadRequestError":
            raise VirustotalError(f"Invalid request made: {e.message}")
        elif e.code == "WrongCredentialsError":
            raise VirustotalError("Invalid API key")

        raise VirustotalError(f"Virustotal request failed: {e.message}")

def fileinfo_request(file_hash):
    with vt.Client(_vt_api_key) as client:
        result = _do_info_request(client, f"/files/{file_hash}")
        if not result:
            return None

        return _make_results(
            avs=result.last_analysis_results,
            stats=result.last_analysis_stats
        )

def urlinfo_request(url):
    with vt.Client(_vt_api_key) as client:
        result =  _do_info_request(client, f"/urls/{vt.url_id(url)}")
        if not result:
            return None

        return _make_results(
            avs=result.last_analysis_results,
            stats=result.last_analysis_stats
        )

def submit_file(path):
    if Path(path).stat().st_size > MAX_VT_FILE_SIZE:
        raise VirustotalError(
            f"The maximum file submission size is: {MAX_VT_FILE_SIZE}"
        )

    with vt.Client(_vt_api_key) as client:
        with open(path, "rb") as fp:
            try:
                vt_submission = client.scan_file(fp, wait_for_completion=False)
            except aiohttp.ClientError as e:
                raise VirustotalError(f"Virustotal connection error: {e}")
            except vt.error.APIError as e:
                if e.code == "BadRequestError":
                    raise VirustotalError(f"Invalid request made: {e.message}")
                elif e.code == "WrongCredentialsError":
                    raise VirustotalError("Invalid API key")

                raise VirustotalError(
                    f"Virustotal request failed: {e.message}")


    return vt_submission.id

def wait_completed(submission_id, timeout=300):
    startime = time.monotonic()
    with vt.Client(_vt_api_key) as client:
        while True:
            analysis = _do_info_request(client, f"/analyses/{submission_id}")
            if analysis.status == 'completed':
                return _make_results(
                    avs=analysis.results,
                    stats=analysis.stats
                )

            if time.monotonic() - startime >= timeout:
                return None

            # Timeout taken from VT's own API. We are not using their
            # wait API because it does not have a timeout.
            time.sleep(20)
