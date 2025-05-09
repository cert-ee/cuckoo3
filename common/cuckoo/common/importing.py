# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import stat
import uuid
import zipfile
from pathlib import Path
from threading import RLock

from . import analyses
from .clients import ImportControllerClient, ActionFailedError
from .storage import (
    AnalysisPaths,
    TaskPaths,
    split_analysis_id,
    create_analysis_folder,
    Binaries,
    File,
    Paths,
    move_file,
    delete_file,
    TASK_PREFIX,
    taskdir_name,
    merge_logdata,
)
from .strictcontainer import Analysis, Task


class AnalysisImportError(Exception):
    pass


class AnalysisExistsError(Exception):
    pass


class AnalysisZippingError(AnalysisImportError):
    pass


def _read_analysisjson(zipped_analysis, passwordbytes=None):
    zip_file = zipped_analysis.zip_fp
    if passwordbytes:
        zip_file.setpassword(passwordbytes)

    try:
        analysisfile = zip_file.getinfo("analysis.json")
    except KeyError:
        raise AnalysisImportError("Invalid analysis zip. Missing file analysis.json")

    # Ignore analysis.json if larger than 50MB. It should never be
    # that big. It is a relatively small JSON structure. We are not
    # even going to try and parse something that large.
    if analysisfile.file_size > 50 * 1024 * 1024:
        raise AnalysisImportError("Analysis.json exceeds 50MB")

    try:
        return Analysis.from_string(zip_file.read("analysis.json"))
    except (ValueError, KeyError, TypeError) as e:
        raise AnalysisImportError(f"Invalid analysis.json: {e}")


def _read_taskjson(zipped_analysis, task_id, passwordbytes=None):
    zip_file = zipped_analysis.zip_fp
    if passwordbytes:
        zip_file.setpassword(passwordbytes)

    taskdir = taskdir_name(task_id)
    try:
        taskfile = zip_file.getinfo(f"{taskdir}/task.json")
    except KeyError:
        raise AnalysisImportError("Invalid analysis zip. Missing file task.json")

    # Ignore task.json if larger than 50MB. It should never be
    # that big. It is a relatively small JSON structure. We are not
    # even going to try and parse something that large.
    if taskfile.file_size > 50 * 1024 * 1024:
        raise AnalysisImportError("task.json exceeds 50MB")

    try:
        return Task.from_string(zip_file.read(f"{taskdir}/task.json"))
    except (ValueError, KeyError, TypeError) as e:
        raise AnalysisImportError(f"Invalid task.json: {e}")


_ILLEGAL_CHARS = ("..", ":", "\x00")


def zinfo_has_illegal_chars(zipinfo):
    name = zipinfo.filename
    return any(c in name for c in _ILLEGAL_CHARS) or name.startswith("/")


def should_ignore_zinfo(zipinfo):
    info = zipinfo.external_attr >> 16
    # Ignore everything that is not a regular file or directory.
    # We don't zip them, so we also don't unzip them.
    # Python3 zipfile does not (currently) support unpacking symlinks,
    # but there are requests and code reviews for it.
    if not stat.S_ISREG(info) and not stat.S_ISDIR(info):
        return True

    # To prevent zip bombs, skip files with a high compression ratio.
    if zipinfo.compress_size > 0:
        if zipinfo.file_size / zipinfo.compress_size > 1500:
            return True

    return False


def _get_unzippables(zipped_data, passwordbytes=None, ignore_filesnames=[]):
    zip_file = zipped_data.zip_fp

    unzippables = []
    if passwordbytes:
        zip_file.setpassword(passwordbytes)

    for file in zip_file.filelist:
        if zinfo_has_illegal_chars(file):
            raise AnalysisImportError(
                f"Illegal characters in path of file: {file.filename}"
            )

        if should_ignore_zinfo(file):
            continue

        if file.filename in ignore_filesnames:
            continue

        unzippables.append(file.filename)

    return unzippables


def _unzip_zipped_data(zipped_data, unzip_path, unzippables=[], passwordbytes=None):
    if not os.path.isdir(unzip_path):
        raise AnalysisImportError(f"Unzip path is not a directory: {unzip_path}")

    if not unzippables:
        unzippables = _get_unzippables(zipped_data, passwordbytes=passwordbytes)

    if not unzippables:
        raise AnalysisImportError("Nothing to unzip after filtering")

    zipped_data.zip_fp.extractall(path=unzip_path, members=unzippables)


class ZippedData:
    def __init__(self, zipfile_path):
        self._path = zipfile_path
        self._fp = None
        self._zfp = None
        self._lock = RLock()

    @property
    def path(self):
        return self._path

    @property
    def fp(self):
        if not self._fp:
            return self.open_buffreader()

        return self._fp

    @property
    def zip_fp(self):
        if not self._zfp:
            return self.open_zipfile()

        return self._zfp

    def unzip(self, unpack_path):
        _unzip_zipped_data(self, unpack_path)

    def get_zipinfo(self, filename):
        try:
            info = self.zip_fp.getinfo(filename)
        except KeyError:
            return None

        if not should_ignore_zinfo(info):
            return info

        return None

    def open_zipfile(self):
        with self._lock:
            try:
                self._zfp = zipfile.ZipFile(self._path, "r")
            except zipfile.BadZipFile as e:
                raise AnalysisImportError(f"Invalid analysis zip. {e}")

            return self._zfp

    def close_zipfile(self):
        with self._lock:
            if self._zfp:
                self._zfp.close()
            return self._zfp

    def open_buffreader(self):
        with self._lock:
            self._fp = open(self._path, "rb")

            return self._fp

    def close_buffreader(self):
        with self._lock:
            if self._fp:
                self._fp.close()

    def delete(self):
        with self._lock:
            delete_file(self._path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fp:
            self.close_buffreader()
        if self._zfp:
            self.close_zipfile()


class ZippedAnalysis(ZippedData):
    def __init__(self, zipfile_path):
        super().__init__(zipfile_path)
        self._analysis = None

    @property
    def analysis(self):
        if not self._analysis:
            self._analysis = _read_analysisjson(self)

        return self._analysis


class ZippedTaskResult(ZippedData):
    def unzip(self, unpack_path):
        # Never overwrite task.json. It should never be edited by a node.
        # Unpack task.log separately and append its contents to the existing
        # task.log
        unzippables = _get_unzippables(
            self, ignore_filesnames=["task.json", "task.log"]
        )
        _unzip_zipped_data(self, unpack_path, unzippables=unzippables)


class ZippedNodeWork(ZippedAnalysis):
    TASK_ID_FILE = "nodework"

    def __init__(self, zipfile_path):
        super().__init__(zipfile_path)
        self._task_id = None
        self._task_name = None
        self._task = None

    @property
    def task_id(self):
        if not self._task_id:
            self._find_task_id()

        return self._task_id

    @property
    def taskdir_name(self):
        if not self._task_name:
            self._find_task_id()

        return self._task_name

    def _find_task_id(self):
        nodework_info = self.zip_fp.getinfo(self.TASK_ID_FILE)
        if not nodework_info:
            raise AnalysisImportError(f"Missing {self.TASK_ID_FILE} in node work zip")

        if should_ignore_zinfo(nodework_info):
            raise AnalysisImportError(f"{self.TASK_ID_FILE} is not a regular file")

        # This file only contains a task ID, and should therefore never be
        # larger than date + analysis id length + _XXX
        if nodework_info.file_size > 30:
            raise AnalysisImportError(f"{self.TASK_ID_FILE} file exceeds maximum size")

        task_id = self.zip_fp.read(nodework_info).decode()
        try:
            self._task_name = taskdir_name(task_id)
        except ValueError as e:
            raise AnalysisImportError(e)

        self._task_id = task_id

    @property
    def task(self):
        if not self._task:
            self._task = _read_taskjson(self, self.task_id)

        return self._task

    def unzip(self, unpack_path, task_only=False):
        """Unzip the current zip to the unpack path. If task_only is
        true, the task_id will be used to search for a matching directory
        name in the zip, and only unpack that."""
        unpack_path = Path(unpack_path)
        taskdir = unpack_path.joinpath(self.taskdir_name)
        if taskdir.exists():
            raise AnalysisImportError(f"Task path {taskdir} already exists")

        all_unzippables = _get_unzippables(self)

        # Remove the task id file. We never want to actually unpack it
        # to disk.
        all_unzippables.remove(self.TASK_ID_FILE)

        if task_only:
            # The analysis directory already exists. Filter out all
            # files that are not in the task_name directory.
            for unzippable in all_unzippables[:]:
                if not unzippable.startswith(self.taskdir_name):
                    all_unzippables.remove(unzippable)

        self.zip_fp.extractall(path=unpack_path, members=all_unzippables)


class Zipper:
    WRAPPER_CLASS = ZippedData

    @property
    def archive_root(self):
        raise NotImplementedError

    def _get_all_zippables(self):
        """Must return a list of (fullpath, archive path) tuples that should
        be added to the zip"""
        raise NotImplementedError

    def _make_zippable_dir(self, dirpath):
        relpath = os.path.relpath(dirpath, self.archive_root)
        if not relpath.endswith("/"):
            relpath += "/"

        info = zipfile.ZipInfo(filename=relpath)
        # Set the external attribute such that is represents a directory
        info.external_attr = stat.S_IFDIR << 16
        return (None, info, None)

    def _make_zippable_file(self, filepath):
        return (
            filepath,
            zipfile.ZipInfo.from_file(
                filename=filepath, arcname=os.path.relpath(filepath, self.archive_root)
            ),
            None,
        )

    def _make_zippable_data(self, archive_path, data):
        info = zipfile.ZipInfo(filename=archive_path)
        info.external_attr = stat.S_IFREG << 16
        return (None, info, data)

    def make_zip(self, zip_path):
        if os.path.exists(zip_path):
            raise AnalysisZippingError(f"Path already exists: {zip_path}")

        with zipfile.ZipFile(
            zip_path, "x", compression=zipfile.ZIP_STORED, allowZip64=True
        ) as zipf:
            for fullpath, zipinfo, data in self._get_all_zippables():
                if zipinfo.is_dir():
                    zipf.writestr(zipinfo, "")
                elif data:
                    zipf.writestr(zipinfo, data)
                else:
                    zipf.write(fullpath, arcname=zipinfo.filename)

        return self.WRAPPER_CLASS(zip_path)


class TaskZipper(Zipper):
    def __init__(self, analysis_id, task_id):
        self.analysis_id = analysis_id
        self.task_id = task_id

        self._arcroot = None

    @property
    def archive_root(self):
        if not self._arcroot:
            self._arcroot = AnalysisPaths.path(self.analysis_id)

        return self._arcroot

    def _get_task_zippables(self, ignore_filenames=[]):
        task_path = TaskPaths.path(self.task_id)
        zippables = []
        for curpath, dirs, files in os.walk(task_path, followlinks=False):
            for dirname in dirs:
                # Always add all directories, even if empty.
                zippables.append(
                    self._make_zippable_dir(os.path.join(curpath, dirname))
                )

            for name in files:
                if name in ignore_filenames:
                    continue

                zippables.append(self._make_zippable_file(os.path.join(curpath, name)))

        return zippables

    def _get_all_zippables(self):
        return self._get_task_zippables()


class TaskResultZipper(TaskZipper):
    WRAPPER_CLASS = ZippedTaskResult

    def __init__(self, task_id):
        super().__init__(None, task_id)

    @property
    def archive_root(self):
        if not self._arcroot:
            self._arcroot = TaskPaths.path(self.task_id)

        return self._arcroot

    def _get_all_zippables(self):
        return self._get_task_zippables(ignore_filenames=["task.json"])


class NodeWorkZipper(TaskZipper):
    WRAPPER_CLASS = ZippedNodeWork

    def _get_all_zippables(self):
        zippables = []
        zippables.extend(self._get_task_zippables())
        zippables.append(
            self._make_zippable_file(AnalysisPaths.analysisjson(self.analysis_id))
        )

        targetzip = AnalysisPaths.zipified_file(self.analysis_id)
        # Set resolve to False, because the binary path is a symlink
        # and we want a relative path to the actual symlink in the
        # analysis directory, not its value.
        submitted_file = AnalysisPaths.submitted_file(self.analysis_id, resolve=False)
        if targetzip.is_file():
            zippables.append(self._make_zippable_file(targetzip))
        elif submitted_file.is_file():
            zippables.append(self._make_zippable_file(submitted_file))

        zippables.append(
            self._make_zippable_data(ZippedNodeWork.TASK_ID_FILE, self.task_id)
        )

        return zippables


class AnalysisZipper(Zipper):
    WRAPPER_CLASS = ZippedAnalysis

    def __init__(self, analysis_id, ignore_dirs=[], ignore_files=[]):
        self.id = analysis_id
        self.ignore_files = tuple(ignore_files)
        self.ignore_dirs = tuple(ignore_dirs)

        self._arcroot = None
        self._check_valid()

    @property
    def archive_root(self):
        if not self._arcroot:
            self._arcroot = AnalysisPaths.path(self.id)

        return self._arcroot

    def _check_valid(self):
        try:
            Analysis.from_file(AnalysisPaths.analysisjson(self.id))
        except (FileNotFoundError, KeyError, ValueError, TypeError) as e:
            raise AnalysisZippingError(
                f"Invalid analysis JSON. Cannot zip analysis: {e}"
            )

    def _add_task(self, task_path):
        zippables = []
        for curpath, dirs, files in os.walk(task_path, followlinks=False):
            for dirname in dirs:
                # Always add all directories, even if empty.
                zippables.append(
                    self._make_zippable_dir(os.path.join(curpath, dirname))
                )

            for name in files:
                fullpath = os.path.join(curpath, name)
                relpath = os.path.relpath(fullpath, task_path)

                # Only add the file if its relative path does not appear
                # in the ignored file or directory list.
                if not relpath.startswith(self.ignore_dirs + self.ignore_files):
                    zippables.append(self._make_zippable_file(fullpath))

        return zippables

    def _add_dir(self, path):
        zippables = []
        for curpath, dirs, files in os.walk(path, followlinks=False):
            for name in files:
                fullpath = os.path.join(curpath, name)
                zippables.append(self._make_zippable_file(fullpath))

        return zippables

    def _get_all_zippables(self):
        zippables = []
        for fullpath in self.archive_root.iterdir():
            if fullpath.is_dir():
                if fullpath.name.startswith(TASK_PREFIX):
                    zippables.extend(self._add_task(fullpath))
                else:
                    zippables.extend(self._add_dir(fullpath))
            else:
                zippables.append(self._make_zippable_file(fullpath))

        return zippables


def _import_targetfile(analysis):
    tmpbin = AnalysisPaths.path(analysis.id).joinpath(f".{uuid.uuid4()}")
    binary = AnalysisPaths.submitted_file(analysis.id)

    try:
        file_helper = File(binary)
    except FileNotFoundError:
        raise AnalysisImportError("Missing binary from imported analysis")

    try:
        binary_helper = Binaries.store(Paths.binaries(), file_helper)
    except IOError as e:
        raise AnalysisImportError(e)

    os.rename(binary, tmpbin)
    binary_helper.symlink(binary)
    delete_file(tmpbin)


def import_analysis(analysis_zip_path, delete_after_import=False):
    if not analysis_zip_path.endswith(".zip"):
        raise AnalysisImportError("File name must be in YYYYMMDD-identifier.zip")

    zipped_analysis = ZippedAnalysis(analysis_zip_path)
    analysis = zipped_analysis.analysis
    try:
        day, identifier = split_analysis_id(analysis.id)
    except ValueError as e:
        raise AnalysisImportError(e)

    try:
        analysis_id, path = create_analysis_folder(day, identifier)
    except FileExistsError:
        raise AnalysisImportError(f"Analysis with id {analysis.id!r} already exists")

    with zipped_analysis:
        zipped_analysis.unzip(path)

    analysis = Analysis.from_file(AnalysisPaths.analysisjson(analysis_id))
    if analysis.category == "file":
        _import_targetfile(analysis)

    try:
        analyses.track_imported(analysis)
    except analyses.AnalysisError as e:
        raise AnalysisImportError(f"Tracking import failed: {e}")

    if delete_after_import:
        zipped_analysis.delete()

    return analysis


def store_importable(zip_path):
    if not zip_path.endswith(".zip"):
        raise AnalysisImportError("File must have a .zip extension")

    analysis_id = ZippedAnalysis(zip_path).analysis.id
    importable_path = Paths.importables(f"{analysis_id}.zip")
    if analyses.exists(analysis_id) or os.path.exists(importable_path):
        raise AnalysisExistsError(
            f"Analysis {analysis_id} already exists or is still in the "
            f"importables directory"
        )

    try:
        move_file(zip_path, importable_path)
    except OSError as e:
        raise AnalysisImportError(f"Failed to write importable zip to Cuckoo cwd: {e}")


def list_importables():
    """Return a list of names of importables that are not processed yet."""
    return os.listdir(Paths.importables())


def notify():
    """Send a ping to the state controller to ask it to track all untracked
    analyses. Newly submitted analyses will not be tracked until the state
    controller receives a notify message."""
    try:
        ImportControllerClient.notify(Paths.unix_socket("importcontroller.sock"))
    except ActionFailedError as e:
        raise AnalysisImportError(
            f"Failed to notify import controller of new analyses. "
            f"Is import mode running? {e}"
        )


def unpack_noderesult(zip_path, task_id):
    task_path = TaskPaths.path(task_id)
    if not task_path.exists():
        raise AnalysisImportError(
            f"Cannot unpack, task path {task_path} does not exist."
        )

    result = ZippedTaskResult(zip_path)
    logfile = result.get_zipinfo("task.log")
    if logfile:
        merge_logdata(TaskPaths.tasklog(task_id), result.zip_fp.read(logfile))

    result.unzip(task_path)
