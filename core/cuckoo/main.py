# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import click
import platform
import logging

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
    if not os.path.exists(Paths.monitor()):
        if ctx.invoked_subcommand == "getmonitor":
            return

        exit_error(
            "No monitor and stager binaries are present yet. "
            "Use 'cuckoo getmonitor <zip path>' to unpack and use monitor "
            "and stagers from a Cuckoo monitor zip."
        )

    if quiet:
        ctx.loglevel = logging.WARNING
    elif debug:
        ctx.loglevel = logging.DEBUG
    else:
        ctx.loglevel = logging.INFO

    if ctx.invoked_subcommand:
        return

    from cuckoo.common.startup import StartupError
    from cuckoo.common.shutdown import (
        register_shutdown, call_registered_shutdowns
    )
    from .startup import start_cuckoo


    def _stopmsg():
        print("Stopping Cuckoo..")

    register_shutdown(_stopmsg, order=1)

    try:
        start_cuckoo(ctx.loglevel)
    except StartupError as e:
        exit_error(f"Failure during Cuckoo startup: {e}")
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

@main.group()
def machine():
    """Add machines to machinery configuration files."""
    pass

@machine.command("add")
@click.argument("machinery")
@click.argument("name")
@click.argument("label")
@click.argument("ip")
@click.argument("platform")
@click.option("--os-version", type=str, help="The version of the platform installed on the machine")
@click.option("--snapshot", type=str, help="A snapshot to use when restoring, other than the default snapshot.")
@click.option("--interface", type=str, help="The network interface that should be used to create network dumps.")
@click.option("--tags", default="", type=str, help="A comma separated list of tags that identify what dependencies/software is installed on the machine.")
def machine_add(machinery, name, label, ip, platform, os_version, snapshot,
                interface, tags):
    """Add a machine to a machinery configuration file."""
    from .startup import add_machine, StartupError
    try:
        add_machine(
            machinery, name=name, label=label, ip=ip, platform=platform,
            os_version=os_version, snapshot=snapshot, interface=interface,
            tags=list(filter(None, [t.strip() for t in tags.split(",")]))
        )
        print_info(f"Added machine {name} to machinery {machinery}")
    except StartupError as e:
        exit_error(f"Failed to add machine. {e}")

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
    from cuckoo.common import submit
    from cuckoo.common.storage import  enumerate_files

    try:
        submit.load_machines_dump()
    except submit.SubmissionError as e:
        exit_error(f"Submission failed: {e}")

    try:
        s_maker = submit.SettingsMaker()
        s_maker.set_timeout(timeout)
        s_maker.set_priority(priority)
        s_maker.set_manual(False)

        for p_v in platform:
            # Split platform,version into usable values
            platform_version = p_v.split(",", 1)

            if len(platform_version) == 2:
                s_maker.add_platform(
                    platform=platform_version[0],
                    os_version=platform_version[1]
                )
            else:
                s_maker.add_platform(platform=platform_version[0])

        settings = s_maker.make_settings()
    except submit.SubmissionError as e:
        exit_error(f"Submission failed: {e}")

    files = []
    for path in target:
        files.extend(enumerate_files(path))

    try:
        for path in files:
            try:
                analysis_id = submit.file(
                    path, settings, file_name=os.path.basename(path)
                )
                print_info(f"Submitted. {analysis_id} -> {path}")
            except submit.SubmissionError as e:
                print_error(f"Failed to submit {path}. {e}")
    finally:
        try:
            submit.notify()
        except submit.SubmissionError as e:
            print_warning(e)


@main.group(invoke_without_command=True)
@click.option("-h", "--host", default="localhost", help="Host to bind the development web interface server on")
@click.option("-p", "--port", default=8000, help="Port to bind the development web interface server on")
@click.pass_context
def web(ctx, host, port):
    if ctx.invoked_subcommand:
        return

    from cuckoo.web.web.startup import init_web, start_web
    init_web(
        ctx.parent.cwd_path, ctx.parent.loglevel, logfile=Paths.log("web.log")
    )
    start_web(host, port)

@web.command("djangocommand")
@click.argument("django_args", nargs=-1)
@click.pass_context
def djangocommand(ctx, django_args):
    """Arguments for this command are passed to Django."""
    from cuckoo.web.web.startup import(
        djangocommands, set_path_settings, init_web
    )

    if "runserver" in django_args:
        init_web(
            ctx.parent.parent.cwd_path, ctx.parent.parent.loglevel,
            logfile=Paths.log("web.log")
        )
    else:
        set_path_settings()

    djangocommands(*django_args)
