# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import click
import logging
import platform


from cuckoo.common.storage import cuckoocwd, Paths

from cuckoo.common.log import (
    exit_error, print_info, print_error, print_warning
)

@click.group(invoke_without_command=True)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.option("-d", "--debug", is_flag=True, help="Enable verbose logging")
@click.option("-q", "--quiet", is_flag=True, help="Only log warnings and critical messages")
@click.pass_context
def main(ctx, cwd, debug, quiet):
    if platform.system().lower() != "linux":
        exit_error(
            "Currently Cuckoo3 is still in development and "
            "will only run on Linux."
        )

    if not cwd:
        cwd = cuckoocwd.DEFAULT

    ctx.cwd_path = cwd
    if not cuckoocwd.exists(cwd):
        if ctx.invoked_subcommand == "createcwd":
            return

        exit_error(
            f"Cuckoo CWD {cwd} does not yet exist. Run "
            f"'cuckoo createcwd' if this is the first time you are "
            f"running Cuckoo with this CWD path"
        )

    cuckoocwd.set(cwd)
    if quiet:
        ctx.loglevel = logging.WARNING
    elif debug:
        ctx.loglevel = logging.DEBUG
    else:
        ctx.loglevel = logging.INFO

    if ctx.invoked_subcommand:
        return

    if not Paths.monitor().exists():
        exit_error(
            "No monitor and stager binaries are present yet. "
            "Use 'cuckoo getmonitor <zip path>' to unpack and use monitor "
            "and stagers from a Cuckoo monitor zip."
        )

    from cuckoo.common.startup import StartupError
    from cuckoo.common.shutdown import (
        register_shutdown, call_registered_shutdowns
    )
    from .startup import start_remote

    def _stopmsg():
        print("Stopping Cuckoo node..")

    register_shutdown(_stopmsg, order=1)

    try:
        start_remote(ctx.loglevel)
    except StartupError as e:
        exit_error(f"Failure during Cuckoo node startup: {e}")
    finally:
        call_registered_shutdowns()

@main.command("createcwd")
@click.option("--regen-configs", is_flag=True)
@click.pass_context
def create_cwd(ctx, regen_configs):
    """Create the specified Cuckoo CWD"""
    from cuckoo.common.startup import StartupError
    from cuckoo.common.startup import create_configurations

    cwd_path = ctx.parent.cwd_path
    if os.path.isdir(ctx.parent.cwd_path):
        if not regen_configs:
            exit_error(f"Path {cwd_path} already exists.")

        if not cuckoocwd.is_valid(cwd_path):
            exit_error(
                f"Path {cwd_path} is not a valid Cuckoo CWD. "
                f"Cannot regenerate configurations."
            )

        try:
            create_configurations()
            print_info("Re-created missing configuration files")
            return
        except StartupError as e:
            exit_error(f"Failure during configuration generation: {e}")

    cuckoocwd.create(cwd_path)
    cuckoocwd.set(cwd_path)
    try:
        create_configurations()
        print_info(f"Created Cuckoo CWD at: {cwd_path}")
    except StartupError as e:
        exit_error(f"Failure during configuration generation: {e}")

@main.command("getmonitor")
@click.argument("zip_path")
def get_monitor(zip_path):
    """Use the monitor and stager binaries from the given
    Cuckoo monitor zip file."""
    from cuckoo.common.guest import unpack_monitor_components
    if not os.path.isfile(zip_path):
        exit_error(f"Zip file does not exist: {zip_path}")

    unpack_monitor_components(zip_path, cuckoocwd.root)