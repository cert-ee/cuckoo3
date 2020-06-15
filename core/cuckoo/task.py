# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from . import db, machinery
from cuckoo.common.storage import TaskPaths, make_task_id

from cuckoo.processing import typehelpers

class TaskCreationError(Exception):
    pass

class Task(typehelpers.StrictContainer):

    FIELDS = {
        "number": int,
        "id": str,
        "platform": str,
        "os_version": str,
        "machine_tags": list,
        "machine": str
    }
    ALLOW_EMPTY = ("machine", "machine_tags", "os_version")


def _create_task(analysis_id, task_number, platform, machine_tags,
                 machine=None):
    task_id = make_task_id(analysis_id, task_number)

    print(f"Creating task {task_id}")
    task_path = TaskPaths.path(task_id)
    try:
        os.mkdir(task_path)
    except FileExistsError as e:
        raise TaskCreationError(
            f"Task directory '{task_path}' creation failed. "
            f"Already exists: {e}"
        )

    task_values = {
        "number": task_number,
        "id": task_id,
        "analysis": analysis_id,
        "platform": platform,
        "os_version": "",
        "machine_tags": machine_tags,
        "machine": machine or ""
    }

    task = Task(**task_values)
    task.to_file(TaskPaths.taskjson(task_id))
    return task_values

def create_all(analysis):
    tasks = []
    tasknum = 1

    if analysis.settings.machines:
        for name in analysis.settings.machines:
            machine = machinery.get_by_name(name)
            if not machine:
                raise TaskCreationError(f"Machine {name} does not exist")

            tasks.append(_create_task(
                analysis_id=analysis.id, task_number=tasknum,
                platform=machine.platform, machine_tags=[],
                machine=machine.name
            ))
            tasknum += 1
    else:
        for platform in analysis.settings.platforms:
            tasks.append(_create_task(
                analysis_id=analysis.id, task_number=tasknum,
                platform=platform, machine_tags=analysis.settings.machine_tags
            ))
            tasknum += 1

    # Set the default state for each task dict
    for task_dict in tasks:
        task_dict["state"] = db.TaskStates.PENDING
        task_dict["machine_tags"] = ",".join(task_dict["machine_tags"])

    ses = db.dbms.session()
    try:
        ses.bulk_insert_mappings(db.Task, tasks)
        ses.commit()
    finally:
        ses.close()
