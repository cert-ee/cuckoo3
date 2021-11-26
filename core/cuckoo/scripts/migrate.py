# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import click

from cuckoo.common.storage import cuckoocwd
from cuckoo.common.log import exit_error

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

    cuckoocwd.set(cwd)

    if ctx.invoked_subcommand:
        return

@main.command("database")
@click.argument("name", type=str)
def migrate_database(name):
    from cuckoo.common.migrate import DBMigrator, MigrationError

    try:
        if name == "all":
            DBMigrator.migrate_all()
        else:
            DBMigrator.migrate(name)
    except MigrationError as e:
        exit_error(e)
