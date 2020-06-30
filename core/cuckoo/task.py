# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from . import db, machinery
from cuckoo.common.storage import TaskPaths, make_task_id
from cuckoo.common.strictcontainer import Task, Errors

class TaskCreationError(Exception):
    pass

def _create_task(analysis_id, task_number, platform, os_version, machine_tags,
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

    for dirname in ("logs",):
        os.mkdir(os.path.join(task_path, dirname))

    task_values = {
        "kind": db.AnalysisKinds.STANDARD,
        "number": task_number,
        "id": task_id,
        "analysis_id": analysis_id,
        "platform": platform,
        "os_version": os_version,
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
                platform=platform["platform"],
                os_version=platform["os_version"],
                machine_tags=analysis.settings.machine_tags
            ))
            tasknum += 1

    # Set the default state for each task dict
    for task_dict in tasks:
        task_dict["state"] = db.TaskStates.PENDING
        task_dict["machine_tags"] = ",".join(task_dict["machine_tags"])
        task_dict["created_on"] = analysis.created_on
        task_dict["priority"] = analysis.settings.priority

    ses = db.dbms.session()
    try:
        ses.bulk_insert_mappings(db.Task, tasks)
        ses.commit()
    finally:
        ses.close()

    return tasks

def set_db_state(task_id, state):
    ses = db.dbms.session()
    try:
        ses.query(db.Task).filter_by(id=task_id).update({"state": state})
        ses.commit()
    finally:
        ses.close()

def merge_run_errors(task_id):
    errpath = TaskPaths.runerr_json(task_id)
    if not os.path.exists(errpath):
        return

    taskpath = TaskPaths.taskjson(task_id)
    task = Task.from_file(taskpath)
    errs = Errors.from_file(errpath)
    if task.errors:
        task.errors.merge_errors(errs)
    else:
        task.errors = errs

    # Update the pre json file
    task.to_file_safe(taskpath)
    os.remove(errpath)
