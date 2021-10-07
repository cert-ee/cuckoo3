# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from pathlib import Path

from . import analyses
from .storage import AnalysisPaths, TaskPaths, Paths, Binaries
from .strictcontainer import (
    Analysis, Task, Identification, Pre, Post, StrictContainer
)
from .machines import Machine
from .clients import (
    APIError, APIServerError, APIDoesNotExistError, ClientError
)

class ResultError(Exception):
    pass

class ResultDoesNotExistError(ResultError):
    pass

class InvalidResultDataError(ResultError):
    pass

class Results:
    ANALYSIS = "analysis"
    TASK = "task"
    IDENTIFICATION = "identification"
    PRE = "pre"
    POST = "post"
    MACHINE = "machine"

class Result:

    def __init__(self, analysis_id):
        self.analysis_id = analysis_id
        self._analysis = None

    def load_requested(self, missing_report_default=None):
        raise NotImplementedError

    def _load_analysis(self):
        try:
            self._analysis = Analysis.from_file(
                AnalysisPaths.analysisjson(self.analysis_id)
            )
        except FileNotFoundError:
            raise ResultDoesNotExistError(
                f"Analysis {self.analysis_id} not found"
            )
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid analysis.json: {e}")

    @property
    def analysis(self):
        if not self._analysis:
            self._load_analysis()

        return self._analysis

    def to_dict(self):
        raise NotImplementedError

class AnalysisResult(Result):

    def __init__(self, analysis_id, include):
        super().__init__(analysis_id)
        self.analysis_id = analysis_id
        self._include = include

        self._analysis = None
        self._pre = None
        self._identification = None

    def load_requested(self, missing_report_default=None):
        if Results.ANALYSIS in self._include:
            self._load_analysis()
        if Results.PRE in self._include:
            self._load_pre(missing_report_default)
        if Results.IDENTIFICATION in self._include:
            self._load_identification(missing_report_default)

    @property
    def pre(self):
        if not self._pre:
            self._load_pre()

        return self._pre

    @property
    def identification(self):
        if not self._identification:
            self._load_identification()

        return self._identification

    @property
    def submitted_file(self):
        return self._get_submitted_file_fp()

    def _load_pre(self, missing_default=None):
        raise NotImplementedError

    def _load_identification(self, missing_default=None):
        raise NotImplementedError

    def _get_submitted_file_fp(self):
        raise NotImplementedError

    def to_dict(self):
        d = {}
        if self._analysis:
            d["analysis"] = self._analysis.to_dict()
        if self._pre is not None:
            d["pre"] = self._pre if not isinstance(self._pre, StrictContainer)\
                else self._pre.to_dict()
        if self._identification is not None:
            d["identification"] = self._identification if not \
                isinstance(self._identification, StrictContainer) \
                else self._identification.to_dict()

        return d

class LocalAnalysisResult(AnalysisResult):

    def _load_pre(self, missing_default=None):
        try:
            self._pre = Pre.from_file(AnalysisPaths.prejson(self.analysis_id))
        except FileNotFoundError:
            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Pre report for analysis {self.analysis_id} not found"
                )
            self._pre = missing_default
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid pre.json: {e}")

    def _load_identification(self, missing_default=None):
        try:
            self._identification = Identification.from_file(
                AnalysisPaths.identjson(self.analysis_id)
            )
        except FileNotFoundError:
            if missing_default is None:
                raise ResultDoesNotExistError(
                    "Identification report for analysis "
                    f"{self.analysis_id} not found"
                )
            self._identification = missing_default
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(
                f"Invalid identification.json: {e}"
            )

    def _get_submitted_file_fp(self):
        path = AnalysisPaths.submitted_file(self.analysis_id, resolve=True)
        if not path.is_file():
            raise ResultDoesNotExistError(
                f"No submitted file found for analysis {self.analysis_id}"
            )

        return open(path, "rb")


class TaskResult(Result):

    def __init__(self, analysis_id, task_id, include):
        super().__init__(analysis_id)
        self.task_id = task_id
        self.analysis_id = analysis_id
        self._include = include

        self._analysis = None
        self._task = None
        self._post = None
        self._machine = None

    def _load_task(self):
        raise NotImplementedError

    def _load_post(self, missing_default=None):
        raise NotImplementedError

    def _load_machine(self, missing_default=None):
        raise NotImplementedError

    def _get_pcap_fp(self):
        raise NotImplementedError

    def _get_screenshot_fp(self, name):
        raise NotImplementedError

    def load_requested(self, missing_report_default=None):
        if Results.ANALYSIS in self._include:
            self._load_analysis()
        if Results.TASK in self._include:
            self._load_task()
        if Results.POST in self._include:
            self._load_post(missing_report_default)
        if Results.MACHINE in self._include:
            self._load_machine(missing_report_default)

    @property
    def task(self):
        if not self._task:
            self._load_task()

        return self._task

    @property
    def post(self):
        if not self._post:
            self._load_post()

        return self._post

    @property
    def machine(self):
        if not self._machine:
            self._load_machine()

        return self._machine

    @property
    def pcap(self):
        return self._get_pcap_fp()

    def screenshot(self, name):
        return self._get_screenshot_fp(name)

    def to_dict(self):
        d = {}
        if self._analysis:
            d["analysis"] = self._analysis.to_dict()
        if self._task:
            d["task"] = self._task.to_dict()
        if self._post is not None:
            d["post"] = self._post if not \
                isinstance(self._post, StrictContainer)\
                else self._post.to_dict()
        if self._machine is not None:
            d["machine"] = self._machine if not \
                isinstance(self._machine, Machine) \
                else self._machine.to_dict()

        return d

class LocalTaskResult(TaskResult):

    def _load_task(self):
        try:
            self._task = Task.from_file(TaskPaths.taskjson(self.task_id))
        except FileNotFoundError:
            raise ResultDoesNotExistError(f"Task {self.task_id} not found")
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid task.json: {e}")

    def _load_post(self, missing_default=None):
        try:
            self._post = Post.from_file(TaskPaths.report(self.task_id))
        except FileNotFoundError:
            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Post report for task {self.task_id} not found"
                )
            self._post = missing_default
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid report.json: {e}")

    def _load_machine(self, missing_default=None):
        try:
            self._machine = Machine.from_file(
                TaskPaths.machinejson(self.task_id)
            )
        except FileNotFoundError:
            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Machine dump for task {self.task_id} not found"
                )
            self._machine = missing_default
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(
                f"Invalid machine.json: {e}"
            )

    def _get_pcap_fp(self):
        pcap_path = TaskPaths.pcap(self.task_id)
        if not pcap_path.is_file():
            raise ResultDoesNotExistError("No PCAP found for task")

        return open(pcap_path, "rb")

    def _get_screenshot_fp(self, name):
        screenshot_path = TaskPaths.screenshot(self.task_id, name)
        if not screenshot_path.is_file():
            raise ResultDoesNotExistError("No such screenshot found for task")

        return open(screenshot_path, "rb")

class RemoteTask(TaskResult):

    def __init__(self, analysis_id, task_id, api_client, data={}, include=[]):
        super().__init__(analysis_id, task_id, include)
        self._data = data
        self._api = api_client

    def _load_task(self):
        d = self._data.get("task")
        if not d:
            if Results.TASK not in self._include:
                raise ResultError("Task was not added to include list")

            raise ResultDoesNotExistError(
                f"Task {self.task_id} not found"
            )

        try:
            self._task = Task(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid task.json: {e}")

    def _load_analysis(self):
        d = self._data.get("analysis")
        if not d:
            if Results.ANALYSIS not in self._include:
                raise ResultError("Analysis was not added to include list")

            raise ResultDoesNotExistError(
                f"Analysis {self.analysis_id} not found"
            )

        try:
            self._analysis = Analysis(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid analysis.json: {e}")

    def _load_machine(self, missing_default=None):
        d = self._data.get("machine")
        if not d:
            if Results.MACHINE not in self._include:
                raise ResultError("Machine was not added to include list")

            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Machine dump for task {self.task_id} not found"
                )
            self._machine = missing_default
        try:
            self._machine = Machine(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid machine.json: {e}")

    def _load_post(self, missing_default=None):
        d = self._data.get("post")
        if not d:
            if Results.POST not in self._include:
                raise ResultError("Post was not added to include list")

            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Post report for task {self.task_id} not found"
                )
            self._post = missing_default
        try:
            self._post = Post(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid report.json: {e}")

    def _get_pcap_fp(self):
        try:
            return self._api.task_pcap(self.analysis_id, self.task_id)
        except APIDoesNotExistError:
            raise ResultDoesNotExistError("No PCAP found for task")
        except ClientError as e:
            raise ResultError(f"Failed to retrieve PCAP: {e}")

    def _get_screenshot_fp(self, name):
        try:
            return self._api.task_screenshot(
                self.analysis_id, self.task_id, name
            )
        except APIDoesNotExistError:
            raise ResultDoesNotExistError("No such screenshot found for task")
        except ClientError as e:
            raise ResultError(f"Failed to retrieve screenshot: {e}")

class RemoteAnalysis(AnalysisResult):

    def __init__(self, analysis_id, api_client, data={}, include=[]):
        super().__init__(analysis_id, include)
        self._data = data
        self._api = api_client

    def _load_analysis(self):
        d = self._data.get("analysis")
        if not d:
            if Results.ANALYSIS not in self._include:
                raise ResultError("Analysis was not added to include list")

            raise ResultDoesNotExistError(
                f"Analysis {self.analysis_id} not found"
            )

        try:
            self._analysis = Analysis(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid analysis.json: {e}")

    def _load_pre(self, missing_default=None):
        d = self._data.get("pre")
        if not d:
            if Results.PRE not in self._include:
                raise ResultError("Pre was not added to include list")

            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Pre report for analysis {self.analysis_id} not found"
                )
            self._pre = missing_default
        try:
            self._pre = Pre(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(f"Invalid pre.json: {e}")

    def _load_identification(self, missing_default=None):
        d = self._data.get("identification")
        if not d:
            if Results.IDENTIFICATION not in self._include:
                raise ResultError(
                    "Identification was not added to include list"
                )

            if missing_default is None:
                raise ResultDoesNotExistError(
                    f"Identification report for analysis {self.analysis_id} "
                    "not found"
                )
            self._identification = missing_default
        try:
            self._identification = Identification(**d)
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidResultDataError(
                f"Invalid identification.json: {e}"
            )

    def _get_submitted_file_fp(self):
        try:
            return self._api.submitted_file(self.analysis_id)
        except APIDoesNotExistError:
            raise ResultDoesNotExistError(
                f"No submitted file found for analysis {self.analysis_id}"
            )
        except ClientError as e:
            raise ResultError(f"Failed to retrieve submitted file: {e}")

class ResultRetriever:

    def __init__(self):
        self.api_client = None

    def set_api_client(self, api_client):
        self.api_client = api_client

    def _search_remote_task(self, analysis_id, task_id, include):
        location = analyses.db_find_location(analysis_id)
        if location != analyses.AnalysisLocation.REMOTE:
            raise ResultDoesNotExistError(
                f"Analysis {analysis_id} does not exist."
            )

        if not include:
            return RemoteTask(
                analysis_id, task_id, self.api_client, {}, include
            )

        try:
            data = self.api_client.task_composite(
                analysis_id, task_id, retrieve=include
            )
        except APIDoesNotExistError:
            raise ResultDoesNotExistError(f"Task {task_id} not found")
        except APIServerError as e:
            raise InvalidResultDataError(e)
        except APIError as e:
            raise ResultError(e)

        return RemoteTask(analysis_id, task_id, self.api_client, data, include)

    def get_task(self, analysis_id, task_id, include=[]):
        if not isinstance(include, list):
            include = list(include)

        if not analyses.exists(analysis_id):
            if self.api_client:
                return self._search_remote_task(analysis_id, task_id, include)

            raise ResultDoesNotExistError(
                f"Analysis {analysis_id} with task {task_id} does not "
                f"exist."
            )

        return LocalTaskResult(analysis_id, task_id, include)

    def _search_remote_analysis(self, analysis_id, include):
        location = analyses.db_find_location(analysis_id)
        if location != analyses.AnalysisLocation.REMOTE:
            raise ResultDoesNotExistError(
                f"Analysis {analysis_id} does not exist."
            )

        if not include:
            return RemoteAnalysis(
                analysis_id, self.api_client, {}, include
            )

        try:
            data = self.api_client.analysis_composite(
                analysis_id, retrieve=include
            )
        except APIDoesNotExistError:
            raise ResultDoesNotExistError(f"Analysis {analysis_id} not found")
        except APIServerError as e:
            raise InvalidResultDataError(e)
        except APIError as e:
            raise ResultError(e)

        return RemoteAnalysis(analysis_id, data, include)

    def get_analysis(self, analysis_id, include=[]):
        if not isinstance(include, list):
            include = list(include)

        if not analyses.exists(analysis_id):
            if self.api_client:
                return self._search_remote_analysis(analysis_id, include)

            raise ResultDoesNotExistError(
                f"Analysis {analysis_id} does not exist."
            )

        return LocalAnalysisResult(analysis_id, include)

    def get_binary(self, sha256):
        try:
            path = Path(Binaries.path(Paths.binaries(), sha256)[0])
        except ValueError:
            raise ResultError("Invalid sha256 hash given")

        if not path.is_file():
            raise ResultDoesNotExistError("Binary not found")

        return open(path, "rb")


retriever = ResultRetriever()
