# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import click
import logging
import os

from cuckoo.common.log import exit_error, print_info, VERBOSE
from cuckoo.common.storage import (
    cuckoocwd, Paths, StorageDirs, CWDError
)

@click.group(invoke_without_command=True)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.option("-h", "--host", default="localhost", help="Host to bind the node API server on")
@click.option("-p", "--port", default=8090, help="Port to bind the node API server on")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging, including for non-Cuckoo modules")
@click.option("-d", "--debug", is_flag=True, help="Enable verbose logging")
@click.option("-q", "--quiet", is_flag=True, help="Only log warnings and critical messages")
@click.pass_context
def main(ctx, host, port, cwd, debug, quiet, verbose):
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

    try:
        cuckoocwd.set(cwd, analyses_dir=StorageDirs.NODE_WORK)
    except CWDError as e:
        exit_error(f"Failed to set Cuckoo working directory: {e}")

    if verbose:
        ctx.loglevel = VERBOSE
    elif debug:
        ctx.loglevel = logging.DEBUG
    elif quiet:
        ctx.loglevel = logging.WARNING
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
        start_remote(ctx.loglevel, api_host=host, api_port=port)
    except StartupError as e:
        exit_error(f"Failure during Cuckoo node startup: {e}")
    finally:
        call_registered_shutdowns()

@main.command("createcwd")
@click.option("--regen-configs", is_flag=True)
@click.option("--update-directories", is_flag=True)
@click.pass_context
def create_cwd(ctx, update_directories, regen_configs):
    """Create the specified Cuckoo CWD"""
    from cuckoo.common.startup import StartupError
    from cuckoo.common.startup import create_configurations

    cwd_path = ctx.parent.cwd_path
    if os.path.isdir(ctx.parent.cwd_path):
        if not regen_configs and not update_directories:
            exit_error(f"Path {cwd_path} already exists.")

        if not cuckoocwd.is_valid(cwd_path):
            exit_error(
                f"Path {cwd_path} is not a valid Cuckoo CWD. "
                f"Cannot regenerate configurations."
            )

        if regen_configs:
            try:
                create_configurations()
                print_info("Re-created missing configuration files")
                return
            except StartupError as e:
                exit_error(f"Failure during configuration generation: {e}")

        if update_directories:
            try:
                cuckoocwd.update_missing()
                print_info("Created missing directories")
                return
            except InvalidCWDError as e:
                exit_error(f"Failed during directory updating: {e}")

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
