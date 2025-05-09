# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import logging
import click

from cuckoo.common.storage import cuckoocwd, CWDError, Paths
from cuckoo.common.log import exit_error, print_warning


@click.group(invoke_without_command=True)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.pass_context
def main(ctx, cwd):
    if not cwd:
        cwd = cuckoocwd.DEFAULT

    ctx.cwd_path = cwd
    if not cuckoocwd.exists(cwd):
        exit_error(
            f"Cuckoo CWD {cwd} does not yet exist. Run "
            f"'cuckoo createcwd' if this is the first time you are "
            f"running Cuckoo with this CWD path"
        )
    try:
        cuckoocwd.set(cwd, skip_migration_check=True)
    except CWDError as e:
        exit_error(f"Failed to set Cuckoo working directory: {e}")

    if ctx.invoked_subcommand:
        from cuckoo.common.startup import init_global_logging

        init_global_logging(
            logging.DEBUG, Paths.log("migrations.log"), use_logqueue=False
        )
        return


@main.command("database")
@click.argument("name", type=str)
def migrate_database(name):
    """Migrate Cuckoo SQL databases to their newer schema versions.
    Migrations perform by Alembic. Use 'all' to migrate all databases."""
    from cuckoo.common.migrate import DBMigrator, MigrationError

    try:
        if name == "all":
            DBMigrator.migrate_all()
        else:
            DBMigrator.migrate(name)
    except MigrationError as e:
        exit_error(e)


@main.command("cwdfiles")
@click.option(
    "--overwrite",
    is_flag=True,
    help="Skip confirmation and overwrite file(s) when user-modified files are detected.",
)
@click.option(
    "--delete-unused",
    is_flag=True,
    help="Remove files from CWD that Cuckoo no longer uses",
)
def migrate_cwdfiles(overwrite, delete_unused):
    """Overwrite files in the CWD to their newer version(s)."""
    from cuckoo.common.migrate import CWDFileMigrator

    for migratable in CWDFileMigrator.find_migratable_files():
        if migratable.unknown_hash and not overwrite:
            print_warning(
                f"'{migratable.cwdpath}' has an unexpected file hash. "
                f"It looks like it was modified by something else than a "
                f"migration. "
                f"Overwriting the file is needed to continue migrating. "
                f"It is recommended to create a backup before continuing"
            )
            if not click.confirm(f"Overwrite file?"):
                exit_error("CWD files migration aborted.")

        migratable.do_migrate(remove_deleted=delete_unused)

    cuckoocwd.write_versions_file(cuckoocwd.root)


@main.command("configs")
def migrate_configs():
    """Attempts to automatically migrate configuration files to a newer
    version. This is needed after a (subpackage) update."""
    from cuckoo.common.migrate import ConfigMigrator, MigrationError

    try:
        ConfigMigrator.migrate_all()
    except MigrationError as e:
        exit_error(e)
