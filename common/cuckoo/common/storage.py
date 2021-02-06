# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import hashlib
import json
import os
import pathlib
import random
import shutil
import string
import uuid
from tempfile import gettempdir
from datetime import datetime

from .packages import find_cuckoo_packages, get_cwdfiles_dir

import sflock

class CWDNotSetError(Exception):
    pass

class InvalidCWDError(Exception):
    pass

_allowed_deletion_dirs = set()

def _add_deletion_dir(path):
    realpath = os.path.realpath(path)
    if realpath == "/":
        raise OSError("Root path deletion not allowed")

    _allowed_deletion_dirs.add(realpath)

def _remove_deletion_dir(path):
    _allowed_deletion_dirs.discard(os.path.realpath(path))

def _deletion_allowed(path):
    return os.path.realpath(path).startswith(tuple(_allowed_deletion_dirs))

if not _allowed_deletion_dirs:
    _add_deletion_dir(gettempdir())

class _CuckooCWD:

    DEFAULT = pathlib.Path.home().joinpath(".cuckoocwd")

    def __init__(self):
        self._dir = None

    @property
    def root(self):
        if not self._dir:
            raise CWDNotSetError(
                "The Cuckoo CWD must be set before performing any actions "
                "that read from or write to it."
            )

        return self._dir

    @staticmethod
    def exists(path):
        return os.path.isdir(path)

    @staticmethod
    def is_valid(path):
        return os.path.isfile(os.path.join(path, ".cuckoocwd"))

    @staticmethod
    def have_permission(path):
        return os.access(path, os.R_OK | os.W_OK | os.X_OK)

    def set(self, path):
        if not _CuckooCWD.exists(path):
            raise InvalidCWDError(f"Cuckoo CWD {path} does not exist.")

        if not _CuckooCWD.is_valid(path):
            raise InvalidCWDError(f"{path} is not a Cuckoo CWD.")

        if not _CuckooCWD.have_permission(path):
            raise InvalidCWDError(
                f"Read, write, and execute access to the Cuckoo CWD is "
                f"required. One or more permissions is missing on {path}."
            )

        if self._dir:
            _remove_deletion_dir(self._dir)

        self._dir = path
        os.environ["CUCKOO_CWD"] = str(path)
        _add_deletion_dir(self._dir)

    @staticmethod
    def create(path):
        if os.path.exists(path):
            raise IsADirectoryError(f"Directory {path} already exists.")

        os.makedirs(path)
        for dirname in ("storage", "conf", "operational", "log"):
            os.makedirs(os.path.join(path, dirname))

        for dirname in ("analyses", "binaries", "untracked",
                        "importables", "exported"):
            os.mkdir(os.path.join(path, "storage", dirname))

        for dirname in ("sockets", "generated"):
            os.mkdir(os.path.join(path, "operational", dirname))

        _CuckooCWD._add_package_cwdfiles(path)
        pathlib.Path(path).joinpath(".cuckoocwd").touch()

    @staticmethod
    def _add_package_cwdfiles(path):
        for fullname, name, package in find_cuckoo_packages():
            pkg_cwd_files = get_cwdfiles_dir(package)
            if not pkg_cwd_files:
                continue


            for entry in os.listdir(pkg_cwd_files):

                entry_path = os.path.join(pkg_cwd_files, entry)
                cwd_entry = os.path.join(path, entry)
                if os.path.exists(cwd_entry):
                    continue

                if os.path.isfile(entry_path):
                    shutil.copyfile(entry_path, cwd_entry)

                elif os.path.isdir(entry_path):
                    shutil.copytree(entry_path, cwd_entry)

cuckoocwd = _CuckooCWD()

_ANALYSIS_ID_LEN = 6

def split_analysis_id(analysis_id):
        date_analysis = analysis_id.split("-", 1)
        if len(date_analysis) != 2:
            raise ValueError(
                "Invalid analysis ID given. Format must be "
                f"YYYYMMDD-identifier. Given: {analysis_id}"
            )

        if len(date_analysis[1]) != _ANALYSIS_ID_LEN:
            raise ValueError(
                f"Invalid identifier length. Must be {_ANALYSIS_ID_LEN} "
                f"characters. Given: {date_analysis[1]}"
            )

        if not date_analysis[1].isalnum():
            raise ValueError(
                "Invalid analysis ID given. ID part can only contain "
                f"A-Z and 0-9. Given {date_analysis[1]}"
            )

        if len(date_analysis[0]) != len("YYYYMMDD"):
            raise ValueError(
                "Date part must be in YYYYMMDD format. "
                f"Given: {date_analysis[0]}"
            )

        return date_analysis

def split_task_id(task_id):

    analysis_id_tasknumber = task_id.split("_", 1)
    if len(analysis_id_tasknumber) != 2:
        raise ValueError(
            f"Invalid task ID given. Format must be "
            f"analysisid_tasknumber. Not: {task_id}"
        )

    date, analysis = split_analysis_id(analysis_id_tasknumber[0])
    return date, analysis, analysis_id_tasknumber[1]

def task_to_analysis_id(task_id):
    date, analysis, _ = split_task_id(task_id)
    return f"{date}-{analysis}"


def make_task_id(analysis_id, task_number):
    return f"{analysis_id}_{task_number}"

class AnalysisPaths:

    @staticmethod
    def _path(analysis_id, *args):
        date, analysis = split_analysis_id(analysis_id)
        return os.path.join(
            cuckoocwd.root, "storage", "analyses", date, analysis, *args
        )

    @staticmethod
    def path(analysis_id):
        return AnalysisPaths._path(analysis_id)

    @staticmethod
    def analysisjson(analysis_id):
        return AnalysisPaths._path(analysis_id, "analysis.json")

    @staticmethod
    def identjson(analysis_id):
        return AnalysisPaths._path(analysis_id, "identification.json")

    @staticmethod
    def prejson(analysis_id):
        return AnalysisPaths._path(analysis_id, "pre.json")

    @staticmethod
    def submitted_file(analysis_id):
        return os.path.realpath(AnalysisPaths._path(analysis_id, "binary"))

    @staticmethod
    def filetree(analysis_id):
        return AnalysisPaths._path(analysis_id, "filetree.json")

    @staticmethod
    def filemap(analysis_id):
        return AnalysisPaths._path(analysis_id, "filemap.json")

    @staticmethod
    def zipified_file(analysis_id):
        return AnalysisPaths._path(analysis_id, "target.zip")

    @staticmethod
    def processingerr_json(analysis_id):
        return AnalysisPaths._path(analysis_id, "processing_errors.json")

    @staticmethod
    def analysislog(analysis_id):
        return AnalysisPaths._path(analysis_id, "analysis.log")

    @staticmethod
    def analyses(*args):
        return os.path.join(cuckoocwd.root, "storage", "analyses", *args)

    @staticmethod
    def day(day):
        return AnalysisPaths.analyses(day)

class TaskPaths:

    @staticmethod
    def _path(task_id,  *args):
        date, analysis, task_number = split_task_id(task_id)
        return os.path.join(
            cuckoocwd.root, "storage", "analyses", date, analysis,
            f"task_{task_number}", *args
        )

    @staticmethod
    def path(task_id):
        return TaskPaths._path(task_id)

    @staticmethod
    def taskjson(task_id):
        return TaskPaths._path(task_id, "task.json")

    @staticmethod
    def memory_dump(task_id):
        return TaskPaths._path(task_id, "memory.dmp")

    @staticmethod
    def procmem_dump(task_id, filename=None):
        if filename:
            return TaskPaths._path(task_id, "memory", filename)

        return TaskPaths._path(task_id, "memory")

    @staticmethod
    def logfile(task_id, *args):
        return TaskPaths._path(task_id, "logs", *args)

    @staticmethod
    def payloadlog(task_id):
        return TaskPaths._path(task_id, "payload.log")

    @staticmethod
    def machinejson(task_id):
        return TaskPaths._path(task_id, "machine.json")

    @staticmethod
    def runerr_json(task_id):
        return TaskPaths._path(task_id, "run_errors.json")

    @staticmethod
    def processingerr_json(task_id):
        return TaskPaths._path(task_id, "processing_errors.json")

    @staticmethod
    def tasklog(task_id):
        return TaskPaths._path(task_id, "task.log")

    @staticmethod
    def eventlog(task_id, *args):
        return TaskPaths._path(task_id, "events", *args)

    @staticmethod
    def pcap(task_id):
        return TaskPaths._path(task_id, "dump.pcap")

    @staticmethod
    def report(task_id):
        return TaskPaths._path(task_id, "report.json")


class Paths(object):

    @staticmethod
    def unix_socket(sockname):
        return os.path.join(cuckoocwd.root, "operational", "sockets", sockname)

    @staticmethod
    def dbfile():
        return os.path.join(cuckoocwd.root, "cuckoo.db")

    @staticmethod
    def analysis(analysis):
        return AnalysisPaths.path(analysis)

    @staticmethod
    def untracked(analysis=None):
        if analysis:
            return os.path.join(
                cuckoocwd.root, "storage", "untracked", analysis
            )
        return os.path.join(cuckoocwd.root, "storage", "untracked")

    @staticmethod
    def importables(filename=None):
        if filename:
            return os.path.join(
                cuckoocwd.root, "storage", "importables", filename
            )
        return os.path.join(cuckoocwd.root, "storage", "importables")

    @staticmethod
    def exported(filename=None):
        if filename:
            return os.path.join(
                cuckoocwd.root, "storage", "exported", filename
            )
        return os.path.join(cuckoocwd.root, "storage", "exported")

    @staticmethod
    def binaries():
        return os.path.join(cuckoocwd.root, "storage", "binaries")

    @staticmethod
    def machinestates():
        return os.path.join(
            cuckoocwd.root, "operational", "generated", "machinestates.json"
        )

    @staticmethod
    def analyses(*args):
        return os.path.join(cuckoocwd.root, "storage", "analyses", *args)

    @staticmethod
    def config(file=None, subpkg=None):
        args = ["conf"]
        if subpkg:
            args.append(subpkg)
        if file:
            args.append(file)
        return os.path.join(cuckoocwd.root, *tuple(args))

    @staticmethod
    def monitor(*args):
        return os.path.join(cuckoocwd.root, "monitor", *args)

    @staticmethod
    def log(filename):
        return os.path.join(cuckoocwd.root, "log", filename)

    @staticmethod
    def elastic_templates():
        return os.path.join(cuckoocwd.root, "elasticsearch")

    @staticmethod
    def web(*args):
        return os.path.join(cuckoocwd.root, "web", *args)

    @staticmethod
    def signatures(*args):
        return os.path.join(cuckoocwd.root, "signatures", *args)

    @staticmethod
    def pattern_signatures(platform=None):
        pattern_path = os.path.join(Paths.signatures("cuckoo", "pattern"))
        if not platform:
            return pattern_path

        return os.path.join(pattern_path, platform)

    @staticmethod
    def safelist(filename):
        return os.path.join(cuckoocwd.root, "safelist", filename)

    @staticmethod
    def safelist_db():
        return Paths.safelist("safelist.db")


def cwd(*args, **kwargs):
    if kwargs.get("analysis"):
        try:
            date, analysis = kwargs["analysis"].split("-", 1)
        except ValueError:
            raise ValueError(
                "Invalid analysis ID given. Format must be YYYYMMDD-analysis"
            )

        return os.path.join(
            cuckoocwd.root, "storage", "analyses", date, analysis
        )

    elif kwargs.get("day"):
        return os.path.join(
            cuckoocwd.root, "storage", "analyses", str(kwargs["day"])
        )

    elif kwargs.get("socket"):
        return os.path.join(
            cuckoocwd.root, "sockets", str(kwargs["socket"])
        )

    return os.path.join(cuckoocwd.root, *args)


def create_analysis_folder(day, identifier):
    try:
        os.mkdir(cwd(day=day))
    except FileExistsError:
        # Don't handle, as this means it was already created before or at the
        # same time of the mkdir call.
        pass

    analysis = f"{day}-{identifier}"
    analysis_path = AnalysisPaths.path(analysis)
    os.mkdir(analysis_path)

    return analysis, analysis_path


def todays_daydir():
    return datetime.utcnow().date().strftime("%Y%m%d")

def make_analysis_folder():
    """Generates today's day dir and a unique analysis id and its dir and
    returns the analysis id and path to its directory"""
    today = todays_daydir()

    identifier = ''.join(
        random.choices(
            string.ascii_uppercase + string.digits, k=_ANALYSIS_ID_LEN
        )
    )
    try:
        return create_analysis_folder(today, identifier)
    except FileExistsError:
        return make_analysis_folder()

    # TODO create potential subdirs


def safe_copyfile(source, destination):
    """Copies source to destination. Full paths must be provided.
    First copies under a tmp name and create file exclusively when copy has
    finished, then renames tmp file to destination filename.

    :raise: FileExistsError, IOError
    """
    if os.path.exists(destination):
        raise FileExistsError(f"Destination file exists: {destination}")

    dst_dir = os.path.dirname(destination)
    if shutil.disk_usage(dst_dir).free <= os.path.getsize(source):
        raise IOError("Destination does not have enough space to store source")

    tmp_path = os.path.join(dst_dir, f".{uuid.uuid4()}")
    shutil.copyfile(source, tmp_path)

    try:
        open(destination, "x").close()
        os.replace(tmp_path, destination)
    except (OSError, FileExistsError):
        os.unlink(tmp_path)
        raise

def move_file(source, destination):
    if os.path.exists(destination):
        raise FileExistsError(f"Destination file exists: {destination}")

    dst_dir = os.path.dirname(destination)
    if shutil.disk_usage(dst_dir).free <= os.path.getsize(source):
        raise IOError("Destination does not have enough space to store source")

    tmp_path = os.path.join(dst_dir, f".{uuid.uuid4()}")

    # Move file
    os.rename(source, tmp_path)

    try:
        os.replace(tmp_path, destination)
    except (OSError, FileExistsError):
        os.unlink(tmp_path)
        raise

def safe_writedata(data, destination):
    if os.path.exists(destination):
        raise FileExistsError(f"Destination file exists: {destination}")

    dst_dir = os.path.dirname(destination)
    if shutil.disk_usage(dst_dir).free <= len(data):
        raise IOError("Destination does not have enough space to store data")

    tmp_path = os.path.join(dst_dir, f".{uuid.uuid4()}")
    with open(tmp_path, "wb") as fp:
        fp.write(data)

    try:
        open(destination, "x").close()
        os.replace(tmp_path, destination)
    except (OSError, FileExistsError):
        os.unlink(tmp_path)
        raise

def safe_json_dump(destination, data, overwrite=False, **kwargs):
    """json.dump the given data to a temporary file in the same directory as
    the destination and replace the given destination afterwards.

    If overwrite is True, overwrites the destination if it exists."""
    if not overwrite and os.path.exists(destination):
        raise FileExistsError(f"Destination file exists: {destination}")

    dst_dir = os.path.dirname(destination)
    tmp_path = os.path.join(dst_dir, f".{uuid.uuid4()}")

    with open(tmp_path, "w") as fp:
        json.dump(data, fp, **kwargs)

    # TODO use Windows API directly to make replace atomic on Windows.
    try:
        os.replace(tmp_path, destination)
    except OSError:
        os.unlink(tmp_path)
        raise

class Binaries:

    DEPTH = 2

    @staticmethod
    def path(binary_dir, sha256):
        """Returns a path to file and directory where the file is located"""
        if not binary_dir or not sha256 or len(sha256) != 64:
            raise ValueError("A base path and sha256 hash must be given")

        dir_path = binary_dir
        for i in range(Binaries.DEPTH):
            dir_path = os.path.join(dir_path, sha256[i])

        return os.path.join(dir_path, sha256), dir_path

    @staticmethod
    def store(binary_dir, file_helper):
        path, dir_path = Binaries.path(binary_dir, file_helper.sha256)

        try:
            # Try to create the dirs. If they already exist or a race condition
            # occurs, ignore the exists error.
            os.makedirs(dir_path)
        except FileExistsError:
            pass

        try:
            file_helper.copy_to(path)
        except FileExistsError:
            return File(path)

        return File(path)


class _DataHasher:

    def __init__(self, data=None):

        self._progress = False
        self._md5 = None
        self._sha1 = None
        self._sha256 = None
        self._sha512 = None

        if data:
            self.calculate(data)

    @property
    def md5(self):
        if not self._progress:
            raise ValueError("No hashes are calculated. Cannot return any.")

        return self._md5.hexdigest()

    @property
    def sha1(self):
        if not self._progress:
            raise ValueError("No hashes are calculated. Cannot return any.")

        return self._sha1.hexdigest()

    @property
    def sha256(self):
        if not self._progress:
            raise ValueError("No hashes are calculated. Cannot return any.")

        return self._sha256.hexdigest()

    @property
    def sha512(self):
        if not self._progress:
            raise ValueError("No hashes are calculated. Cannot return any.")

        return self._sha512.hexdigest()

    def calculate(self, data_chunk):
        if not self._progress:
            self._md5 = hashlib.md5()
            self._sha1 = hashlib.sha1()
            self._sha256 = hashlib.sha256()
            self._sha512 = hashlib.sha512()
            self._progress = True

        self._md5.update(data_chunk)
        self._sha1.update(data_chunk)
        self._sha256.update(data_chunk)
        self._sha512.update(data_chunk)

class File:

    def __init__(self, file_path):
        self._path = pathlib.Path(file_path)

        if not self.valid():
            raise FileNotFoundError("File does not exist or is not a file")

        self._md5 = None
        self._sha1 = None
        self._sha256 = None
        self._sha512 = None

    @property
    def path(self):
        return str(self._path)

    @property
    def name(self):
        return self._path.name

    @property
    def size(self):
        """Get file size.
        @return: file size.
        """
        return os.path.getsize(self._path)

    @property
    def md5(self):
        """Get MD5.
        @return: MD5.
        """
        if not self._md5:
            self._calc_hashes()
        return self._md5

    @property
    def sha1(self):
        """Get SHA1.
        @return: SHA1.
        """
        if not self._sha1:
            self._calc_hashes()
        return self._sha1

    @property
    def sha256(self):
        """Get SHA256.
        @return: SHA256.
        """
        if not self._sha256:
            self._calc_hashes()
        return self._sha256

    @property
    def sha512(self):
        """
        Get SHA512.
        @return: SHA512.
        """
        if not self._sha512:
            self._calc_hashes()
        return self._sha512

    @property
    def type(self):
        """Get the file type.
        @return: file type.
        """
        return str(sflock.magic.from_file(os.path.realpath(self._path)))

    @property
    def media_type(self):
        """Get MIME content file type (example: image/jpeg).
        @return: file content type.
        """
        return str(sflock.magic.from_file(
            os.path.realpath(self._path), mime=True
        ))

    def valid(self):
        return self._path and self._path.is_file()

    def empty(self):
        return self._path.stat().st_size != 0

    def get_chunks(self, size=16 * 1024 * 1024):
        """Read file contents in chunks (generator)."""
        with open(self._path, "rb") as fd:
            while True:
                chunk = fd.read(size)
                if not chunk:
                    break

                yield chunk

    def _calc_hashes(self):
        """Calculate all possible hashes for this file."""
        hasher = _DataHasher()
        for chunk in self.get_chunks():
            hasher.calculate(chunk)

        self._md5 = hasher.md5
        self._sha1 = hasher.sha1
        self._sha256 = hasher.sha256
        self._sha512 = hasher.sha512

    def copy_to(self, path):
        safe_copyfile(self._path, path)

    def symlink(self, link_path):
        os.symlink(str(self._path), link_path)

    def to_dict(self):
        """Get all information available.
        @return: information dict.
        """
        return {
            "size": self.size,
            "md5": self.md5,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "sha512": self.sha512,
            "media_type": self.media_type,
            "type": self.type
        }

class InMemoryFile:

    def __init__(self, data, name=""):
        self._data = data
        self.name = name

        hasher = _DataHasher(data=data)

        self.md5 = hasher.md5
        self.sha1 = hasher.sha1
        self.sha256 = hasher.sha256
        self.sha512 = hasher.sha512

    @property
    def size(self):
        """Get file size.
        @return: file size.
        """
        return len(self._data)

    @property
    def type(self):
        """Get the file type.
        @return: file type.
        """
        return str(sflock.magic.from_buffer(self._data))

    @property
    def media_type(self):
        """Get MIME content file type (example: image/jpeg).
        @return: file content type.
        """
        return str(sflock.magic.from_buffer(self._data, mime=True))

    def copy_to(self, path):
        safe_writedata(self._data, path)

    def to_dict(self):
        """Get all information available.
        @return: information dict.
        """
        return {
            "size": self.size,
            "md5": self.md5,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "sha512": self.sha512,
            "media_type": self.media_type,
            "type": self.type
        }

def enumerate_files(path):
    """Yields all filepaths from a directory."""
    if os.path.isfile(path):
        yield path

    elif os.path.isdir(path):
        for dirname, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirname, filename)

                if os.path.isfile(filepath):
                    yield filepath

def delete_dirtree(path):
    if not _deletion_allowed(path):
        raise OSError(
            f"Given path {path} is not a part of directories that Cuckoo is "
            f"allowed to delete from: {_allowed_deletion_dirs}"
        )

    shutil.rmtree(path, ignore_errors=False)

def delete_dir(path):
    if not _deletion_allowed(path):
        raise OSError(
            f"Given path {path} is not a part of directories that Cuckoo is "
            f"allowed to delete from: {_allowed_deletion_dirs}"
        )

    os.rmdir(path)

def delete_file(path):
    if not _deletion_allowed(path):
        raise OSError(
            f"Given path {path} is not a part of directories that Cuckoo is "
            f"allowed to delete from: {_allowed_deletion_dirs}"
        )

    os.unlink(path)