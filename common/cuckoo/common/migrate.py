# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os.path

from cuckoo.common.storage import cuckoocwd
from cuckoo.common import packages

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
