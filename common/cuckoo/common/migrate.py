# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os.path
from pathlib import Path

from cuckoo.common import packages
from cuckoo.common.storage import cuckoocwd, File, safe_copyfile, delete_file

class MigrationError(Exception):
    pass

class DBMigrator:

    MIGRATION_DIRNAME = "dbmigrations"
    DBNAMES_PACKAGE = {
        "cuckoodb": "cuckoo.common",
        "safelistdb": "cuckoo.common",
        "taskqueuedb": "cuckoo"
    }

    @classmethod
    def migrate(cls, name, revision="head"):
        name = name.lower()
        db_pkgname = cls.DBNAMES_PACKAGE.get(name)
        if not db_pkgname:
            raise MigrationError(f"Unknown database: '{name}'")

        data = packages.get_data_dir(packages.get_module(db_pkgname))
        migration_dir = os.path.join(data, cls.MIGRATION_DIRNAME, name)

        if not os.path.isdir(migration_dir):
            raise MigrationError(
                f"Failed to migrate database: '{name}'. Migration file "
                f"directory does not exist: {migration_dir}"
            )

        from subprocess import run, CalledProcessError
        try:
            run(
                ["alembic", "-x", f"cwd={str(cuckoocwd.root)}",
                 "upgrade", revision], cwd=migration_dir, check=True
            )
        except CalledProcessError as e:
            raise MigrationError(
                f"Error during migration of '{name}'. "
                f"Alembic exit code: {e.returncode}"
            )

    @classmethod
    def migrate_all(cls):
        errs = []
        for name in cls.DBNAMES_PACKAGE.keys():
            try:
                cls.migrate(name)
            except MigrationError as e:
                errs.append(str(e))

        if errs:
            raise MigrationError(
                f"One or more migrations failed. {', '.join(errs)}"
            )

class _CWDFile:

    class States:

        NEW = "new"
        UPDATED = "updated"
        DELETED = "deleted"

    def __init__(self, relative_path):
        self.relative_path = relative_path

        self.state = self.States.NEW
        self.version_hashes = set()
        self.latest_version = None
        self.changed = False

    def is_known_hash(self, filehash):
        return filehash in self.version_hashes

    def is_latest_version(self, filehash):
        return filehash == self.latest_version

    def add_state(self, state, filehash=None):
        self.state = state
        if filehash:
            self.latest_version = filehash
            self.version_hashes.add(filehash)

    def update(self, state, filehash=None):
        self.add_state(state, filehash)
        self.changed = True

    def __str__(self):
        return f"{self.state},{self.relative_path},{self.latest_version or ''}"

class CWDMigrateFile:

    IGNORE_FILES = [".empty", ".gitkeep"]

    def __init__(self, filepath):
        self.filepath = filepath
        self.cwdfiles = {}

    def load(self):
        if not os.path.isfile(self.filepath):
            return

        with open(self.filepath, "r") as fp:
            for line in fp.readlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                state, relpath, filehash = None, None, None
                entry = list(filter(None, line.split(",", 2)))
                if len(entry) == 3:
                    state, relpath, filehash = entry
                elif len(entry) == 2:
                    # A deleted entry does not need a hash.
                    state, relpath = entry
                else:
                    continue

                if ".." in relpath:
                    raise MigrationError(
                        f"Illegal characters in relative path: {relpath}"
                    )

                cwdfile = self.cwdfiles.get(relpath)
                if cwdfile:
                    cwdfile.add_state(state=state, filehash=filehash)
                else:
                    cwdfile = self.cwdfiles.setdefault(
                        relpath, _CWDFile(relative_path=relpath)
                    )
                    cwdfile.add_state(state=state, filehash=filehash)

    def update_from(self, pkg_cwd_files):
        for existing_cwdfile in self.cwdfiles.values():
            path = os.path.join(pkg_cwd_files, existing_cwdfile.relative_path)
            if not os.path.exists(path):
                existing_cwdfile.update(state=_CWDFile.States.DELETED)

        for currdir, _, currdir_files in os.walk(pkg_cwd_files):
            relpath = os.path.relpath(currdir, pkg_cwd_files)
            if relpath == ".":
                relpath = ""

            for filename in currdir_files:
                if filename in self.IGNORE_FILES:
                    continue

                f = File(os.path.join(currdir, filename))
                relpath_file = os.path.join(relpath, filename)

                cwdfile = self.cwdfiles.get(relpath_file)
                if cwdfile:
                    if not cwdfile.is_latest_version(f.sha1):
                        cwdfile.update(
                            state=_CWDFile.States.UPDATED, filehash=f.sha1
                        )
                else:
                    cwdfile = self.cwdfiles.setdefault(
                        relpath_file, _CWDFile(relative_path=relpath_file)
                    )
                    cwdfile.update(state=_CWDFile.States.NEW, filehash=f.sha1)

    def write(self, comment=""):
        changed = [f"{cwdfile}\n" for cwdfile in self.cwdfiles.values()
                   if cwdfile.changed]
        if not changed:
            return

        changed.sort()
        with open(self.filepath, "a") as fp:
            if comment:
                fp.write(f"# {comment}\n")

            fp.writelines(changed)

class _MigratableFile:

    DELETABLE_EXTENSION = ".old"

    def __init__(self, cwdpath, pkgpath, cwdfile, unknown_hash=False):
        self.pkgpath = pkgpath
        self.cwdpath = cwdpath
        self.cwdfile = cwdfile

        self.unknown_hash = unknown_hash

    def do_migrate(self, remove_deleted=False):
        if self.cwdfile.state in (_CWDFile.States.NEW,
                                  _CWDFile.States.UPDATED):
            safe_copyfile(self.pkgpath, self.cwdpath, overwrite=True)
            print(f"Updated file to latest version: '{self.cwdpath}'")
        elif self.cwdfile.state == _CWDFile.States.DELETED:
            if remove_deleted:
                delete_file(self.cwdpath)
                print(f"Deleted file: {self.cwdpath}")
            else:
                newpath = self.cwdpath.with_name(
                    f"{self.cwdpath.name}{self.DELETABLE_EXTENSION}"
                )
                self.cwdpath.rename(newpath)
                print(f"Soft deleted file: {self.cwdpath} -> {newpath}")

class CWDFileMigrator:

    HASHFILE_NAME = "cwdmigrate.txt"

    @classmethod
    def update_hashfiles(cls, comment=""):
        for fullname, name, package in packages.find_cuckoo_packages():
            cwdfiles_path = packages.get_cwdfiles_dir(package)
            if not cwdfiles_path:
                continue

            print(f"Updating CWD file hashes for package: {fullname}")
            data_path = packages.get_data_dir(package)
            migratefile = CWDMigrateFile(
                os.path.join(data_path, cls.HASHFILE_NAME)
            )
            migratefile.load()
            migratefile.update_from(cwdfiles_path)
            migratefile.write(comment)

    @classmethod
    def _state_new_modified(cls, cwdpath, pkgpath, cwdfile):
        f = File(cwdpath)
        # The file exists and is already the latest version
        if cwdfile.is_latest_version(f.sha1):
            return None

        return _MigratableFile(
            cwdpath=cwdpath, pkgpath=pkgpath, cwdfile=cwdfile,
            unknown_hash=not cwdfile.is_known_hash(f.sha1)
        )

    @classmethod
    def _state_deleted(cls, cwdpath, pkgpath, cwdfile):
        if not cwdpath.exists():
            return None

        return _MigratableFile(
            cwdpath=cwdpath, pkgpath=pkgpath, cwdfile=cwdfile
        )

    @classmethod
    def find_migratable_files(cls):
        # First create all new CWD directories and copy new files.
        cuckoocwd.update_missing()

        for fullname, name, package in packages.find_cuckoo_packages():
            cwdfiles_path = packages.get_cwdfiles_dir(package)
            if not cwdfiles_path:
                continue

            data_path = packages.get_data_dir(package)
            migratefile = CWDMigrateFile(
                os.path.join(data_path, cls.HASHFILE_NAME)
            )
            # Read state, file, and hashes from the cwd migrations txt file.
            # This is used to determine if a file should be updated.
            migratefile.load()

            for relpath, cwdfile in migratefile.cwdfiles.items():
                pkgpath = Path(cwdfiles_path, relpath)
                cwdpath = cuckoocwd.root.joinpath(relpath)
                migratable = None
                if cwdfile.state in (_CWDFile.States.NEW,
                                     _CWDFile.States.UPDATED):
                    migratable = cls._state_new_modified(
                        cwdpath, pkgpath, cwdfile
                    )
                elif cwdfile.state == _CWDFile.States.DELETED:
                    migratable = cls._state_deleted(cwdpath, pkgpath, cwdfile)

                if migratable:
                    yield migratable
