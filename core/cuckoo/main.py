# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import click
import sys
import platform

from cuckoo.common.storage import cuckoocwd, Paths

@click.group(invoke_without_command=True)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.pass_context
def main(ctx, cwd):
    if platform.system().lower() != "linux":
        print(
            "Currently Cuckoo3 is still in development and "
            "will only run on Linux."
        )
        sys.exit(1)

    if not cwd:
        cwd = cuckoocwd.DEFAULT

    ctx.cwd_path = cwd
    if not cuckoocwd.exists(cwd):
        if ctx.invoked_subcommand == "createcwd":
            return

        print(
            f"Cuckoo CWD {cwd} does not yet exist. Run "
            f"'cuckoo createcwd' if this is the first time you are "
            f"running Cuckoo with this CWD path"
        )
        sys.exit(1)

    cuckoocwd.set(cwd)
    if not os.path.exists(Paths.monitor()):
        if ctx.invoked_subcommand == "getmonitor":
            return

        print(
            "No monitor and stager binaries are present yet. "
            "Use 'cuckoo getmonitor <zip path>' to unpack and use monitor "
            "and stagers from a Cuckoo monitor zip."
        )
        sys.exit(1)

    if ctx.invoked_subcommand:
        return

    from .startup import StartupError
    from .shutdown import register_shutdown, call_registered_shutdowns

    def _stopmsg():
        print("Stopping Cuckoo..")

    register_shutdown(_stopmsg, order=1)

    try:
        start_cuckoo()
    except StartupError as e:
        print(f"Failure during Cuckoo startup: {e}")
        sys.exit(1)
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

    print(f"Starting Cuckoo. Using CWD {cuckoocwd.root}")
    print("Loading configurations")
    try:
        load_configurations()
    except MissingConfigurationFileError as e:
        print(f"Missing configuration file: {e}")
        sys.exit(1)

    print("Starting resultserver")
    start_resultserver()
    print("Loading machineries and starting machinery manager")
    start_machinerymanager()
    print("Initializing database")
    init_database()
    print("Starting processing handler and workers")
    start_processing_handler()
    print("Starting task runner")
    start_taskrunner()
    print("Starting state controller")
    start_statecontroller()
    print("Starting scheduler")
    start_scheduler()

@main.command("createcwd")
@click.option("--regen-configs", is_flag=True)
@click.pass_context
def create_cwd(ctx, regen_configs):
    """Create the specified Cuckoo CWD"""
    from .startup import create_configurations

    cwd_path = ctx.parent.cwd_path
    if os.path.isdir(ctx.parent.cwd_path):
        if not regen_configs:
            print(f"Path {cwd_path} already exists.")
            sys.exit(1)

        if not cuckoocwd.is_valid(cwd_path):
            print(
                f"Path {cwd_path} is not a valid Cuckoo CWD. "
                f"Cannot regenerate configurations."
            )
            sys.exit(1)
        create_configurations()
        print("Re-created missing configuration files")
        return


    cuckoocwd.create(cwd_path)
    cuckoocwd.set(cwd_path)
    create_configurations()
    print(f"Create Cuckoo CWD at: {cwd_path}")

@main.command("getmonitor")
@click.argument("zip_path")
def get_monitor(zip_path):
    """Use the monitor and stager binaries from the given
    Cuckoo monitor zip file."""
    from cuckoo.common.guest import unpack_monitor_components
    if not os.path.isfile(zip_path):
        print(f"Zip file does not exist: {zip_path}")
        sys.exit(1)

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
        print(
            "No machines have ever been loaded. "
            "Start Cuckoo to load these from the machine configurations."
        )
        sys.exit(1)

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
        print(f"Failed to submit: {e}")
        sys.exit(1)

    files = []
    for path in target:
        files.extend(enumerate_files(path))

    try:
        for path in files:
            filename = os.path.basename(path)
            try:
                analysis_id = submit.file(File(path), s, file_name=filename)
                print(f"Submitted. {analysis_id} -> {path}")
            except submit.SubmissionError as e:
                print(f"Failed to submit {path}. {e}")
    finally:
        try:
            submit.notify()
        except IPCError as e:
            print(f"Could not notify Cuckoo process. Is Cuckoo running? {e}")
