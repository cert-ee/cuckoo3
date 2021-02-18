# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import stat
from threading import RLock
import uuid
import zipfile

from . import analyses
from .clients import ImportControllerClient, ActionFailedError
from .storage import (
    AnalysisPaths, split_analysis_id, create_analysis_folder, Binaries, File,
    Paths, move_file, delete_file
)
from .strictcontainer import Analysis

class AnalysisImportError(Exception):
    pass

class AnalysisExistsError(Exception):
    pass

class AnalysisZippingError(AnalysisImportError):
    pass

def read_analysisjson(zipped_analysis, passwordbytes=None):
    zip_file = zipped_analysis.zip_fp
    if passwordbytes:
        zip_file.setpassword(passwordbytes)

    try:
        analysisfile = zip_file.getinfo("analysis.json")
    except KeyError:
        raise AnalysisImportError(
            "Invalid analysis zip. Missing file analysis.json"
        )

    # Ignore analysis.json if larger than 50MB. It should never be
    # that big. It is a relatively small JSON structure. We are not
    # even going to try and parse something that large.
    if analysisfile.file_size > 50 * 1024 * 1024:
        raise AnalysisImportError("Analysis.json exceeds 50MB")

    try:
        return Analysis.from_string(zip_file.read("analysis.json"))
    except (ValueError, KeyError, TypeError) as e:
        raise AnalysisImportError(f"Invalid analysis.json: {e}")

def unzip_analysis(zipped_analysis, unzip_path, passwordbytes=None):
    if not os.path.isdir(unzip_path):
        raise AnalysisImportError(
            f"Unzip path is not a directory: {unzip_path}"
        )

    zip_file = zipped_analysis.zip_fp

    illegal = ("..", ":", "\x00")
    unzippables = []
    if passwordbytes:
        zip_file.setpassword(passwordbytes)

    for file in zip_file.filelist:
        name = file.filename
        if any(c in name for c in illegal) or name.startswith("/"):
            raise AnalysisImportError(
                f"Illegal characters in path of file: {name}"
            )

        info = file.external_attr >> 16
        # Ignore everything that is not a regular file or directory.
        # We don't zip them, so we also don't unzip them.
        # Python3 zipfile does not (currently) support unpacking symlinks,
        # but there are requests and code reviews for it.
        if not stat.S_ISREG(info) and not stat.S_ISDIR(info):
            continue

        # To prevent zip bombs, skip files with a high compression ratio.
        if file.file_size / file.compress_size > 1500:
            continue

        unzippables.append(file.filename)

    if not unzippables:
        raise AnalysisImportError("Nothing to unzip after filtering")

    zip_file.extractall(path=unzip_path, members=unzippables)

class AnalysisZipper:

    def __init__(self, analysis_id):
        self.id = analysis_id
        self._rootfiles = []
        self._tasks = {}
        self._check_valid()
        self._discover()

    def _check_valid(self):
        try:
            Analysis.from_file(AnalysisPaths.analysisjson(self.id))
        except (FileNotFoundError, KeyError, ValueError, TypeError) as e:
            raise AnalysisZippingError(
                f"Invalid analysis JSON. Cannot zip analysis: {e}"
            )

    def make_zip(self, zip_path, ignore_task_dirs=[], ignore_task_files=[]):
        if os.path.exists(zip_path):
            raise AnalysisZippingError("Zip path already exists")

        zippables = []
        zippables.extend(self._rootfiles)
        zippables.extend(
            self._make_task_zippables(ignore_task_dirs, ignore_task_files)
        )

        with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_STORED,
                             allowZip64=True) as zipf:
            for zippable in zippables:
                fullpath, arcname = zippable
                if not fullpath:
                    # An empty dir, add it.
                    if arcname.endswith("/"):
                        zipf.writestr(zipfile.ZipInfo(filename=arcname), "")
                else:
                    zipf.write(fullpath, arcname=arcname)

        return ZippedAnalysis(zip_path)

    def _make_task_zippables(self, ignore_dirs=[], ignore_files=[]):
        zippables = []
        for task_name, entries in self._tasks.items():
            for arcname, fullpath in entries.items():
                if arcname.startswith(tuple(ignore_dirs) + tuple(ignore_files)):
                    continue

                zippables.append((fullpath, f"{task_name}/{arcname}"))

            # Create the empty dirs
            for dirname in ignore_dirs:
                zippables.append((None, f"{task_name}/{dirname}/"))

        return zippables

    def _add_task(self, task_name, path):
        task = self._tasks.setdefault(task_name, {})
        for curpath, dirs, files in os.walk(path, followlinks=False):
            for name in files:
                fullpath = os.path.join(curpath, name)
                arcpath = os.path.relpath(fullpath, path)
                task[arcpath] = fullpath

    def _add_dir(self, path, analysis_path):
        for curpath, dirs, files in os.walk(path, followlinks=False):
            for name in files:
                fullpath = os.path.join(curpath, name)
                self._rootfiles.append(
                    (fullpath, os.path.relpath(fullpath, analysis_path))
                )

    def _discover(self):
        analysis_path = AnalysisPaths.path(self.id)
        for name in os.listdir(analysis_path):
            fullpath = os.path.join(analysis_path, name)
            if os.path.isdir(fullpath):
                if name.startswith("task_"):
                    self._add_task(name, fullpath)
                else:
                    self._add_dir(fullpath, analysis_path)
            else:
                self._rootfiles.append(
                    (fullpath, os.path.relpath(fullpath, analysis_path))
                )

class ZippedAnalysis:

    def __init__(self, zipfile_path):
        self._path = zipfile_path
        self._fp = None
        self._zfp = None
        self._analysis = None
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

    @property
    def analysis(self):
        if not self._analysis:
            self._analysis = read_analysisjson(self)

        return self._analysis

    def unzip(self, unpack_path):
        unzip_analysis(self, unpack_path)

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

def _import_targetfile(analysis):
    tmpbin = os.path.join(AnalysisPaths.path(analysis.id), f".{uuid.uuid4()}")
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
    os.remove(tmpbin)

def import_analysis(analysis_zip_path, delete_after_import=False):
    if not analysis_zip_path.endswith(".zip"):
        raise AnalysisImportError(
            "File name must be in YYYYMMDD-identifier.zip"
        )

    zipped_analysis = ZippedAnalysis(analysis_zip_path)
    analysis = zipped_analysis.analysis
    try:
        day, identifier = split_analysis_id(analysis.id)
    except ValueError as e:
        raise AnalysisImportError(e)

    try:
        analysis_id, path = create_analysis_folder(day, identifier)
    except FileExistsError:
        raise AnalysisImportError(
            f"Analysis with id {analysis.id!r} already exists"
        )

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
        raise AnalysisImportError(
            f"Failed to write importable zip to Cuckoo cwd: {e}"
        )

def list_importables():
    """Return a list of names of importables that are not processed yet."""
    return os.listdir(Paths.importables())

def notify():
    """Send a ping to the state controller to ask it to track all untracked
    analyses. Newly submitted analyses will not be tracked until the state
    controller receives a notify message."""
    try:
        ImportControllerClient.notify(
            Paths.unix_socket("importcontroller.sock")
        )
    except ActionFailedError as e:
        raise AnalysisImportError(
            f"Failed to notify import controller of new analyses. "
            f"Is import mode running? {e}"
        )
