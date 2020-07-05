# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import click
import platform
import logging

from cuckoo.common.storage import cuckoocwd, Paths
from cuckoo.common.log import (
    exit_error, print_info, print_error, print_warning, CuckooGlobalLogger
)

@click.group(invoke_without_command=True)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.pass_context
def main(ctx, cwd):
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
    if not os.path.exists(Paths.monitor()):
        if ctx.invoked_subcommand == "getmonitor":
            return

        exit_error(
            "No monitor and stager binaries are present yet. "
            "Use 'cuckoo getmonitor <zip path>' to unpack and use monitor "
            "and stagers from a Cuckoo monitor zip."
        )

    if ctx.invoked_subcommand:
        return

    from .startup import StartupError, init_global_logging
    from .shutdown import register_shutdown, call_registered_shutdowns

    def _stopmsg():
        print("Stopping Cuckoo..")

    register_shutdown(_stopmsg, order=1)

    # Initialize globing logging to cuckoo.log
    init_global_logging(logging.DEBUG, Paths.log("cuckoo.log"))

    try:
        start_cuckoo()
    except StartupError as e:
        exit_error(f"Failure during Cuckoo startup: {e}")
    finally:
        call_registered_shutdowns()

def start_cuckoo():
    from multiprocessing import set_start_method
    set_start_method("spawn")

    from cuckoo.common.config import MissingConfigurationFileError
    from .startup import (
        load_configurations, start_machinerymanager, init_database,
        start_processing_handler, start_statecontroller, start_resultserver,
        start_taskrunner, start_scheduler
    )

    log = CuckooGlobalLogger(__name__)

    log.info(f"Starting Cuckoo.", cwd=cuckoocwd.root)
    log.info("Loading configurations")
    try:
        load_configurations()
    except MissingConfigurationFileError as e:
        log.fatal_error(f"Missing configuration file: {e}", includetrace=False)

    log.info("Starting resultserver")
    start_resultserver()
    log.info("Loading machineries and starting machinery manager")
    start_machinerymanager()
    log.info("Initializing database")
    init_database()
    log.info("Starting processing handler and workers")
    start_processing_handler()
    log.info("Starting task runner")
    start_taskrunner()
    log.info("Starting state controller")
    start_statecontroller()
    log.info("Starting scheduler")
    start_scheduler()

@main.command("createcwd")
@click.option("--regen-configs", is_flag=True)
@click.pass_context
def create_cwd(ctx, regen_configs):
    """Create the specified Cuckoo CWD"""
    from .startup import create_configurations, StartupError

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

@main.command("submit")
@click.argument("target", nargs=-1)
# @click.option(
#     "--machine-tag", multiple=True,
#     help="Additional machine tag to the ones that are automatically selected "
#          "in target identification."
# )
@click.option(
    "--platform", multiple=True,
    help="The platform and optionally the OS version the analysis task must "
         "run on. Specified as platform,osversion or just platform."
)
@click.option("--timeout", type=int, default=120, help="Analysis timeout in seconds")
@click.option("--priority", type=int, default=1, help="The priority of this analysis")
def submission(target, platform, timeout, priority):
    """Create a new file analysis"""
    from . import submit, analyses
    from cuckoo.common.ipc import IPCError
    from cuckoo.common.storage import File, enumerate_files, Paths
    from .machinery import read_machines_dump, set_machines_dump

    if not os.path.exists(Paths.machinestates()):
        exit_error(
            "No machines have ever been loaded. "
            "Start Cuckoo to load these from the machine configurations."
        )

    # Change platform,version to dict with those keys
    platforms = []
    for p_v in platform:
        platform_version = p_v.split(",", 1)

        if len(platform_version) == 2:
            platforms.append({
                "platform": platform_version[0],
                "os_version": platform_version[1]
            })
        else:
            platforms.append({
                "platform": platform_version[0],
                "os_version": ""
            })

    set_machines_dump(read_machines_dump(Paths.machinestates()))

    try:
        s = analyses.Settings(
            timeout=timeout, priority=priority, enforce_timeout=True,
            dump_memory=False, options={}, machine_tags=[],
            platforms=platforms, machines=[], manual=False
        )
    except (ValueError, TypeError, analyses.AnalysisError) as e:
        exit_error(f"Failed to submit: {e}")

    files = []
    for path in target:
        files.extend(enumerate_files(path))

    try:
        for path in files:
            filename = os.path.basename(path)
            try:
                analysis_id = submit.file(File(path), s, file_name=filename)
                print_info(f"Submitted. {analysis_id} -> {path}")
            except submit.SubmissionError as e:
                print_error(f"Failed to submit {path}. {e}")
    finally:
        try:
            submit.notify()
        except IPCError as e:
            print_warning(
                f"Could not notify Cuckoo process. Is Cuckoo running? {e}"
            )
