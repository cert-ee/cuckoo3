# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import click
from tabulate import tabulate

from cuckoo.common.storage import cuckoocwd, CWDError
from cuckoo.common import safelist
from cuckoo.common.log import exit_error, print_info
from cuckoo.common.startup import init_safelist_db, MigrationNeededError


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
        cuckoocwd.set(cwd)
    except CWDError as e:
        exit_error(f"Failed to set Cuckoo working directory: {e}")

    try:
        init_safelist_db()
    except MigrationNeededError as e:
        exit_error(e)

    if ctx.invoked_subcommand:
        return


@main.command()
def listnames():
    """Show all existing safelists and their types."""
    safelists = []
    for name, slclass in safelist.name_safelist.items():
        safelists.append((name, slclass.valuetype, slclass.description))

    print(
        tabulate(
            safelists, headers=("Name", "Value type", "Description"), tablefmt="github"
        )
    )


@main.command("csvdump")
@click.argument("name", type=str)
@click.argument("filepath", type=str)
def dump_csv(filepath, name):
    """Dump a safelist to a CSV file.

    \b
    NAME The name of a safelist to dump
    FILEPATH A path to write the CSV file to
    """
    import os.path

    if os.path.exists(filepath):
        exit_error(f"File {filepath} already exists")

    sl_class = safelist.name_safelist.get(name)
    if not sl_class:
        exit_error(f"Safelist {name} does not exist.")

    try:
        safelist.dump_safelist_csv(filepath, sl_class)
    except safelist.SafelistError as e:
        exit_error(f"Failed to dump safelist: {e}")


@main.command("csvimport")
@click.argument("name", type=str)
@click.argument("filepath", type=str)
def import_csv(name, filepath):
    """Import a safelist from a safelist CSV dump file.

    \b
    NAME The name of the safelist to import the data to
    FILEPATH The filepath of a CSV file containing the data valid for the given
    safelist name
    """
    import os.path

    if not os.path.exists(filepath):
        exit_error(f"File {filepath} does not exist")

    sl_class = safelist.name_safelist.get(name)
    if not sl_class:
        exit_error(f"Safelist {name} does not exist.")

    try:
        safelist.import_csv_safelist(filepath, sl_class)
    except safelist.SafelistError as e:
        exit_error(f"Failed to import safelist: {e}")


@main.command("show")
@click.argument("name", type=str)
def show_safelist(name):
    """Print all entries of the specified safelist.

    \b
    NAME The name of a safelist to print
    """
    sl_class = safelist.name_safelist.get(name)
    if not sl_class:
        exit_error(f"Safelist {name} does not exist.")

    try:
        entries = safelist.get_entries(sl_class.name)
    except safelist.SafelistError as e:
        exit_error(f"Error retrieving safelist: {e}")

    values = []
    for entry in entries:
        values.append(
            (
                entry.id,
                entry.valuetype,
                entry.regex,
                entry.platform,
                entry.value,
                entry.description,
                entry.source,
            )
        )

    headers = ("ID", "Type", "Regex", "Platform", "Value", "Description", "Source")
    print(tabulate(values, headers, tablefmt="github"))


@main.command("add")
@click.argument("name", type=str)
@click.argument("value", type=str)
@click.option(
    "--platform",
    type=str,
    default="",
    help="The platform for which to use this value. No platform means the entry is used for all platforms.",
)
@click.option("--regex", is_flag=True, help="Indicate that the given value is a regex.")
@click.option(
    "--description",
    type=str,
    default="",
    help="A short description of the value and why it is safelisted",
)
@click.option(
    "--source",
    type=str,
    default="",
    help="The source of the safelist value. E.G a URL.",
)
def add_entry(name, value, platform, regex, description, source):
    """Add a value to the specified safelist.

    \b
    NAME The name of the safelist to add a value to
    VALUE The value to add to the safelist"""
    sl_class = safelist.name_safelist.get(name)
    if not sl_class:
        exit_error(f"Safelist {name} does not exist")

    if not value:
        exit_error("Empty value not allowed")

    try:
        sl_class.add_entry(
            value,
            platform=platform,
            regex=regex,
            description=description,
            source=source,
        )
    except safelist.SafelistError as e:
        exit_error(f"Failed to add value to safelist. {e}")

    print_info(f"Added {value!r} to safelist {name!r}")


@main.command("delete")
@click.argument("name", type=str)
@click.argument("ids", type=int, nargs=-1, required=True)
def delete_entries(name, ids):
    """Delete one or more safelist entries by ID.

    \b
    NAME The name of the safelist to add a value to
    IDS One or more safelist entry IDs"""
    sl_class = safelist.name_safelist.get(name)
    if not sl_class:
        exit_error(f"Safelist {name} does not exist")

    try:
        sl_class.delete_entries(ids)
    except safelist.SafelistError as e:
        exit_error(f"Failed to delete safelist entries. {e}")

    print_info(f"Deleted safelist entries {ids}")


@main.command("clear")
@click.argument("name", type=str)
@click.option("--yes", is_flag=True, help="Skip confirmation screen")
def delete_all(name, yes):
    """Delete all entries from the specified safelist.

    \b
    NAME The name of the safelist to clear"""
    sl_class = safelist.name_safelist.get(name)
    if not sl_class:
        exit_error(f"Safelist {name} does not exist")

    if not yes:
        if not click.confirm(f"Delete all entries from safelist '{name}'?"):
            return

    print_info(f"Deleting all entries from safelist '{name}'")
    try:
        sl_class.delete_all()
    except safelist.SafelistError as e:
        exit_error(f"Failed to clear safelist '{name}'. {e}")

    print_info(f"Deleted all entries from safelist '{name}'")
