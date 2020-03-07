# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import click
import os

from .storage import cwd, Paths
from .controller import Controller
from . import ipc, submit

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    if ctx.invoked_subcommand:
        return

    from .db import dbms

    print("Starting")
    dbms.initialize(cwd("cuckoo.db"))
    c = Controller(Paths.unix_socket("controller.sock"))
    c.init()
    c.start()

@main.command("submit")
@click.argument("target", nargs=-1)
def submission(target):
    from .storage import File, enumerate_files

    files = []
    for path in target:
        files.extend(enumerate_files(path))

    s = submit.Settings(
        timeout=60, priority=2, enforce_timeout=False, dump_memory=False,
        options={}, machine_tags=[], platforms=[], machines=[], manual=False
    )
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
        except ipc.IPCError as e:
            print(f"Could not notify controller process {e}")
