# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import click
import logging

from cuckoo.common.storage import cuckoocwd, Paths, InvalidCWDError
from cuckoo.common.log import (
    exit_error, print_info, print_error, print_warning, VERBOSE
)

@click.group(invoke_without_command=True)
@click.option("--cwd", help="Cuckoo Working Directory")
@click.option("--distributed", is_flag=True, help="Start Cuckoo in distributed mode")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging, including for non-Cuckoo modules")
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
@click.option("-q", "--quiet", is_flag=True, help="Only log warnings and critical messages")
@click.option("--cancel-abandoned", is_flag=True, help="Do not recover and cancel tasks that are abandoned and still 'running'")
@click.pass_context
def main(ctx, cwd, distributed, debug, quiet, verbose, cancel_abandoned):
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
        cuckoocwd.set(cwd)
    except InvalidCWDError as e:
        exit_error(f"Invalid Cuckoo working directory: {e}")

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

    if not os.path.exists(Paths.monitor()):
        exit_error(
            "No monitor and stager binaries are present yet. "
            "Use 'cuckoo getmonitor <zip path>' to unpack and use monitor "
            "and stagers from a Cuckoo monitor zip."
        )

    from cuckoo.common.startup import StartupError
    from cuckoo.common.shutdown import (
        register_shutdown, call_registered_shutdowns
    )

    if distributed:
        from .startup import start_cuckoo_controller as start_cuckoo
    else:
        from .startup import start_cuckoo

    def _stopmsg():
        print("Stopping Cuckoo..")

    register_shutdown(_stopmsg, order=1)

    try:
        start_cuckoo(ctx.loglevel, cancel_abandoned=cancel_abandoned)
    except StartupError as e:
        exit_error(f"Failure during Cuckoo startup: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        exit_error(f"Unexpected failure during Cuckoo startup: {e}")
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

@main.group()
def machine():
    """Add machines to machinery configuration files."""
    pass

@machine.command("add")
@click.argument("machinery_name")
@click.argument("machine_name")
@click.argument("config_fields", nargs=-1)
@click.option("--tags", default="", type=str, help="A comma separated list of tags that identify what dependencies/software is installed on the machine.")
def machine_add(machinery_name, machine_name, config_fields, tags):
    """Add a machine to the configuration of the specified machinery.
    config_fields be all non-optional configuration entries in key=value
    format."""
    if not config_fields:
        exit_error(
            f"No configuration fields specified. See the '{machinery_name}' "
            f"machinery configuration file to determine what fields "
            f"must be given"
        )

    machine_dict = {
        "tags": list(filter(None, [t.strip() for t in tags.split(",")]))
    }
    for entry in config_fields:
        try:
            key, value = tuple(filter(None, entry.split("=", 1)))
            if key == "tags":
                exit_error("Use --tags to provide tags")
        except ValueError:
            exit_error(
                f"Invalid argument: {entry}. Each config field must be in "
                f"key=value format."
            )

        machine_dict[key] = value

    from cuckoo.common.startup import StartupError
    from .startup import add_machine

    try:
        add_machine(machinery_name, machine_name, machine_dict)
        print_info(
            f"Added machine: '{machine_name}' to machinery: '{machinery_name}'"
        )
    except StartupError as e:
        exit_error(e)

@machine.command("import")
@click.argument("machinery_name")
@click.argument("vms_path")
@click.argument("machine_names", nargs=-1)
def vmcloak_import(machinery_name, vms_path, machine_names):
    """Import all or 'machine names' from the specified VMCloak vms path to the
    specified machinery module."""
    if not os.path.isdir(vms_path):
        exit_error(f"'{vms_path}' is not a directory")

    if not os.listdir(vms_path):
        exit_error(f"'{vms_path}' is an empty directory")

    from cuckoo.common.startup import StartupError
    from .startup import import_vmcloak_vms
    try:
        imported = import_vmcloak_vms(machinery_name, vms_path, machine_names)
    except StartupError as e:
        exit_error(e)

    if not imported:
        print_warning("No machines imported. Is it the correct directory?")
    else:
        for name in imported:
            print_info(
                f"Imported machine: '{name}' to machinery '{machinery_name}'"
            )

@machine.command("delete")
@click.argument("machinery_name")
@click.argument("machine_names", nargs=-1)
def delete_machines(machinery_name, machine_names):
    """Delete the specified machines from the specified machinery names
    configuration file."""
    if not machine_names:
        exit_error("No machines specified")

    from cuckoo.common.startup import StartupError
    from .startup import delete_machines
    try:
        deleted = delete_machines(machinery_name, machine_names)
    except StartupError as e:
        exit_error(e)

    if not deleted:
        print_warning("No machines deleted. Are the names correct?")
    else:
        for name in deleted:
            print_info(f"Deleted machine: {name}")


def _submit_files(settings, *targets):
    from cuckoo.common import submit
    from cuckoo.common.storage import enumerate_files
    files = []
    for path in targets:
        if not os.path.exists(path):
            yield None, path, "No such file or directory"

        files.extend(enumerate_files(path))

    for path in files:
        try:
            analysis_id = submit.file(
                path, settings, file_name=os.path.basename(path)
            )
            yield analysis_id, path, None
        except submit.SubmissionError as e:
            yield None, path, e

def _submit_urls(settings, *targets):
    from cuckoo.common import submit
    for url in targets:
        try:
            analysis_id = submit.url(url, settings)
            yield analysis_id, url, None
        except submit.SubmissionError as e:
            yield None, url, e

def _parse_settings(**kwargs):
    kv_options = ("option", "route_option")
    for kw, vals in kwargs.items():
        for val in vals:

            plat_index = None
            value = None
            split = val.split(",", 1)
            if len(split) == 2:
                if split[0].isdigit():
                    plat_index = int(split[0]) - 1
                    value = split[1]
                else:
                    value = val
            elif len(split) == 1:
                value = split[0]

            if kw in kv_options:
                try:
                    option, val = value.split("=", 1)
                    value = {option:val}
                except ValueError:
                    yield None, None, None, \
                          f"Invalid option value for {kw}. {val!r}"

            yield plat_index, kw, value, None


@main.command("submit")
@click.argument("target", nargs=-1)
@click.option("-u", "--url", is_flag=True, help="Submit URL(s) instead of files.")
@click.option(
    "--platform", multiple=True,
    help="The platform and optionally the OS version the analysis task must "
         "run on. Specified as platform,osversion or just platform."
)
@click.option("--timeout", type=int, default=120, help="Analysis timeout in seconds.")
@click.option("--priority", type=int, default=1, help="The priority of this analysis.")
@click.option("--orig-filename", is_flag=True, help="Ignore auto detected file extension and use the original file extension.")
@click.option("--browser",  multiple=True, help="The browser to use for a URL analysis.")
@click.option("--command", multiple=True, help="The command/args that should be used to start the target. Enclose in quotes. "
                                "Use %PAYLOAD% where the target should be in the command.")
@click.option("--route-type", multiple=True, help="The route type to use.")
@click.option("--route-option", multiple=True, help="Options for given routes")
def submission(target, url, platform, timeout, priority, orig_filename,
               browser, command, route_type, route_option):
    """Create a new file/url analysis"""
    if not target:
        exit_error("No target specified")

    from cuckoo.common.config import cfg, ConfigurationError
    from cuckoo.common.storage import Paths
    from cuckoo.common import submit
    from cuckoo.common.startup import load_configuration, StartupError

    try:
        load_configuration("analysissettings.yaml")
        submit.settings_maker.set_limits(
            cfg("analysissettings.yaml", "limits")
        )
        submit.settings_maker.set_defaults(
            cfg("analysissettings.yaml", "default")
        )
        submit.settings_maker.set_nodesinfosdump_path(Paths.nodeinfos_dump())
    except (submit.SubmissionError, StartupError, ConfigurationError) as e:
        exit_error(f"Submission failed: {e}")

    try:
        s_helper = submit.settings_maker.new_settings()
        s_helper.set_timeout(timeout)
        s_helper.set_priority(priority)
        s_helper.set_orig_filename(orig_filename)
        s_helper.set_manual(False)

        for p_v in platform:
            # Split platform,version,tags into usable values
            platform_version = p_v.split(",", 2)

            if len(platform_version) == 1:
                s_helper.add_platform(platform=platform_version[0])

            elif len(platform_version) == 2:
                s_helper.add_platform(
                    platform=platform_version[0],
                    os_version=platform_version[1]
                )
            elif len(platform_version) == 3:
                s_helper.add_platform(
                    platform=platform_version[0],
                    os_version=platform_version[1],
                    tags=platform_version[2].split(",")
                )

        for platform_index, setting_key, value, error in _parse_settings(
            browser=browser, command=command, route_type=route_type,
            route_option=route_option
        ):
            if error:
                raise submit.SubmissionError(error)

            s_helper.set_setting(
                setting_key, value, platform_index=platform_index
            )

        settings = s_helper.make_settings()
    except submit.SubmissionError as e:
        exit_error(f"Submission failed: {e}")

    if url:
        submitter, kind = _submit_urls, "URL"
    else:
        submitter, kind = _submit_files, "file"

    try:
        for analysis_id, target, error in submitter(settings, *target):
            if error:
                print_error(f"Failed to submit {kind}: {target}. {error}")
            else:
                print_info(f"Submitted {kind}: {analysis_id} -> {target}")
    finally:
        try:
            submit.notify()
        except submit.SubmissionError as e:
            print_warning(e)


@main.group(invoke_without_command=True)
@click.option("-h", "--host", default="localhost", help="Host to bind the development web interface server on")
@click.option("-p", "--port", default=8000, help="Port to bind the development web interface server on")
@click.option("--autoreload", is_flag=True, help="Automatically reload modified Python files")
@click.pass_context
def web(ctx, host, port, autoreload):
    """Start the Cuckoo web interface (development server)"""
    if ctx.invoked_subcommand:
        return

    from cuckoo.web.web.startup import init_web, start_web
    init_web(
        ctx.parent.cwd_path, ctx.parent.loglevel, logfile=Paths.log("web.log")
    )
    start_web(host, port, autoreload=autoreload)

@web.command("generateconfig")
@click.option("--uwsgi", is_flag=True, help="Generate basic uWSGI configuration to run Cuckoo web")
@click.option("--nginx", is_flag=True, help="Generate basic NGINX configuration to serve static and Cuckoo web run by uWSGI")
def _generate_web_confs(nginx, uwsgi):
    """Generate basic configurations for uWSGI and NGINX"""
    if not nginx and not uwsgi:
        with click.Context(_generate_web_confs) as ctx:
            print(_generate_web_confs.get_help(ctx))

    from cuckoo.common.startup import StartupError
    from cuckoo.web.web.confgen import make_nginx_base, make_uwsgi_base
    try:
        if nginx:
            print(make_nginx_base())
            return
        if uwsgi:
            print(make_uwsgi_base())
            return
    except StartupError as e:
        exit_error(e)

@web.command("djangocommand", context_settings=(dict(ignore_unknown_options=True)))
@click.argument("django_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def webdjangocommand(ctx, django_args):
    """Arguments for this command are passed to Django."""
    from cuckoo.web.web.startup import (
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

@main.group(invoke_without_command=True)
@click.option("-h", "--host", default="localhost", help="Host to bind the development web API server on")
@click.option("-p", "--port", default=8090, help="Port to bind the development web API server on")
@click.option("--autoreload", is_flag=True, help="Automatically reload modified Python files")
@click.pass_context
def api(ctx, host, port, autoreload):
    """Start the Cuckoo web API (development server)"""
    if ctx.invoked_subcommand:
        return

    from cuckoo.web.api.startup import init_api, start_api
    init_api(
        ctx.parent.cwd_path, ctx.parent.loglevel, logfile=Paths.log("api.log")
    )
    start_api(host, port, autoreload=autoreload)

@api.command("generateconfig")
@click.option("--uwsgi", is_flag=True, help="Generate basic uWSGI configuration to run Cuckoo API")
@click.option("--nginx", is_flag=True, help="Generate basic NGINX configuration to serve the Cuckoo web API by uWSGI")
def _generate_api_confs(nginx, uwsgi):
    """Generate basic configurations for uWSGI and NGINX"""
    if not nginx and not uwsgi:
        with click.Context(_generate_api_confs) as ctx:
            print(_generate_api_confs.get_help(ctx))

    from cuckoo.common.startup import StartupError
    from cuckoo.web.api.confgen import make_nginx_base, make_uwsgi_base
    try:
        if nginx:
            print(make_nginx_base())
            return
        if uwsgi:
            print(make_uwsgi_base())
            return
    except StartupError as e:
        exit_error(e)

@api.command("token")
@click.option("-l", "--list", is_flag=True, help="List all current API tokens and their owners")
@click.option("-c", "--create", type=str, help="Create a new API token for a given owner name")
@click.option("--admin", is_flag=True, help="Grant admin priviles to API token being created")
@click.option("-d", "--delete", type=int, help="Delete the specified token by its token ID")
@click.option("--clear", is_flag=True, help="Delete all API tokens")
def apitoken(list, create, admin, delete, clear):
    """List, create, and delete API tokens."""
    from cuckoo.web.api.startup import load_app
    load_app()
    from cuckoo.web.api import apikey
    if list:
        apikey.print_api_keys()
    elif create:
        try:
            key, identifier = apikey.create_key(create, admin)
            print_info(f"Created key {key} with ID: {identifier}")
        except apikey.APIKeyError as e:
            exit_error(f"API token creation failed: {e}")
    elif delete:
        if apikey.delete_key(delete):
            print_info(f"Deleted key with ID {delete}")
    elif clear:
        if click.confirm("Delete all API tokens?"):
            count = apikey.delete_all()
            print_info(f"Deleted {count} API tokens")
    else:
        with click.Context(apitoken) as ctx:
            print(apitoken.get_help(ctx))

@api.command("djangocommand", context_settings=(dict(ignore_unknown_options=True)))
@click.argument("django_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def apidjangocommand(ctx, django_args):
    """Arguments for this command are passed to Django."""
    from cuckoo.web.api.startup import(
        djangocommands, set_path_settings, init_api
    )

    if "runserver" in django_args:
        init_api(
            ctx.parent.parent.cwd_path, ctx.parent.parent.loglevel,
            logfile=Paths.log("api.log")
        )
    else:
        set_path_settings()

    djangocommands(*django_args)

@main.command()
@click.pass_context
def importmode(ctx):
    """Start the Cuckoo import controller."""
    if ctx.invoked_subcommand:
        return

    from cuckoo.common.startup import StartupError
    from cuckoo.common.shutdown import (
        register_shutdown, call_registered_shutdowns
    )
    from .startup import start_importmode

    def _stopmsg():
        print("Stopping import mode..")

    register_shutdown(_stopmsg, order=1)

    try:
        start_importmode(ctx.parent.loglevel)
    except StartupError as e:
        exit_error(f"Failure during import mode startup: {e}")
    finally:
        call_registered_shutdowns()
