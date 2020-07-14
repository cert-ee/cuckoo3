# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from . import db, machinery
from cuckoo.common.storage import TaskPaths, make_task_id
from cuckoo.common.strictcontainer import Task, Errors
from cuckoo.common.log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

class TaskCreationError(Exception):
    def __init__(self, msg, reasons=[]):
        self.reasons = reasons
        super().__init__(msg)

class MissingResourceError(TaskCreationError):
    pass

class NoTasksCreatedError(TaskCreationError):
    pass

class NotAllTasksCreatedError(TaskCreationError):
    pass


def _create_task(analysis_id, task_number, platform="", machine_tags=set(),
                 os_version="", machine_name=None):

    if machine_name:
        if not machinery.get_by_name(machine_name):
            raise MissingResourceError(
                f"Machine {machine_name} does not exist"
            )

    if platform:
        if machine_tags and not isinstance(machine_tags, set):
            machine_tags = set(machine_tags)

        machine = machinery.find(platform, os_version, machine_tags)
        if not machine:
            raise MissingResourceError(
                f"No machine with platform: '{platform}'. "
                f"Os version: '{os_version}'. "
                f"Tags: '{' ,'.join(tag for tag in machine_tags)}'."
            )

    task_id = make_task_id(analysis_id, task_number)
    log.debug("Creating task.", task_id=task_id)
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
        "machine": machine_name or ""
    }

    task = Task(**task_values)
    task.to_file(TaskPaths.taskjson(task_id))
    return task_values

def create_all(analysis):
    tasks = []
    tasknum = 1
    resource_errors = []

    if analysis.settings.machines:
        for machine_name in analysis.settings.machines:
            try:
                tasks.append(_create_task(
                    analysis_id=analysis.id, task_number=tasknum,
                    machine_name=machine_name
                ))
                tasknum += 1
            except MissingResourceError as e:
                resource_errors.append(str(e))
    else:
        for platform in analysis.settings.platforms:
            try:
                tasks.append(_create_task(
                    analysis_id=analysis.id, task_number=tasknum,
                    platform=platform["platform"],
                    os_version=platform["os_version"],
                    machine_tags=analysis.settings.machine_tags
                ))
                tasknum += 1
            except MissingResourceError as e:
                resource_errors.append(str(e))


    if not tasks:
        raise NoTasksCreatedError(
            "No tasks were created", reasons=resource_errors
        )

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

    return tasks, resource_errors

def set_db_state(task_id, state):
    ses = db.dbms.session()
    try:
        ses.query(db.Task).filter_by(id=task_id).update({"state": state})
        ses.commit()
    finally:
        ses.close()

def merge_task_errors(task_id, errors_container):
    taskjson_path = TaskPaths.taskjson(task_id)
    task = Task.from_file(taskjson_path)

    if task.errors:
        task.errors.merge_errors(errors_container)
    else:
        task.errors = errors_container

    task.to_file_safe(taskjson_path)

def merge_run_errors(task_id):
    errpath = TaskPaths.runerr_json(task_id)
    if not os.path.exists(errpath):
        return

    errors_container = Errors.from_file(errpath)
    merge_task_errors(task_id, errors_container)

    os.remove(errpath)
