# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os
import copy

from .storage import TaskPaths, make_task_id
from .strictcontainer import Task, Errors
from .log import CuckooGlobalLogger
from .machines import find_in_lists
from . import db

log = CuckooGlobalLogger(__name__)

class TaskError(Exception):
    pass

class TaskCreationError(TaskError):
    def __init__(self, msg, reasons=[]):
        self.reasons = reasons
        super().__init__(msg)

class MissingResourceError(TaskCreationError):
    pass

class NoTasksCreatedError(TaskCreationError):
    pass

class NotAllTasksCreatedError(TaskCreationError):
    pass

class HumanStates:
    PENDING = "Pending"
    RUNNING = "Running"
    RUN_COMPLETED = "Run completed"
    PENDING_POST = "Pending post"
    REPORTED = "Reported"
    FATAL_ERROR = "Fatal error"

class States:
    PENDING = "pending"
    RUNNING = "running"
    RUN_COMPLETED = "run_completed"
    PENDING_POST = "pending_post"
    REPORTED = "reported"
    FATAL_ERROR = "fatal_error"

    _HUMAN = {
        PENDING: HumanStates.PENDING,
        RUNNING: HumanStates.RUNNING,
        RUN_COMPLETED: HumanStates.RUN_COMPLETED,
        PENDING_POST: HumanStates.PENDING_POST,
        REPORTED: HumanStates.REPORTED,
        FATAL_ERROR: HumanStates.FATAL_ERROR
    }

    @classmethod
    def to_human(cls, state):
        try:
            return cls._HUMAN[state]
        except KeyError:
            raise TaskError(
                f"No human readable version for state {state!r} exists"
            )


def _make_task_dirs(task_id):
    task_path = TaskPaths.path(task_id)
    try:
        os.mkdir(task_path)
    except FileExistsError as e:
        raise TaskCreationError(
            f"Task directory '{task_path}' creation failed. "
            f"Already exists: {e}"
        )

    for dirpath in (TaskPaths.logfile(task_id),
                    TaskPaths.procmem_dump(task_id)):
        os.mkdir(dirpath)


def _create_task(nodes_tracker, analysis, task_number, platform="",
                 machine_tags=set(), os_version="", machine_name=None,
                 platform_settings={}):

    if machine_name:
        if not find_in_lists(nodes_tracker.machine_lists, name=machine_name):
            raise MissingResourceError(
                f"Machine {machine_name} does not exist"
            )

    if platform:
        if machine_tags and not isinstance(machine_tags, set):
            machine_tags = set(machine_tags)

        machine = find_in_lists(
            nodes_tracker.machine_lists, platform=platform,
            os_version=os_version, tags=machine_tags
        )
        if not machine:
            raise MissingResourceError(
                f"No machine with platform: '{platform}'. "
                f"Os version: '{os_version}'. "
                f"Tags: '{', '.join(machine_tags)}'."
            )

    task_id = make_task_id(analysis.id, task_number)
    log.debug("Creating task.", task_id=task_id)

    _make_task_dirs(task_id)
    task_values = {
        "kind": analysis.kind,
        "number": task_number,
        "id": task_id,
        "state": States.PENDING,
        "analysis_id": analysis.id,
        "platform": platform,
        "os_version": os_version,
        "machine_tags": list(machine_tags),
        "machine": machine_name or ""
    }

    if platform_settings:
        task_values.update({
            "command": platform_settings.get("command"),
            "route": platform_settings.get("route"),
            "browser": platform_settings.get("browser")
        })

    task = Task(**task_values)
    task.to_file(TaskPaths.taskjson(task_id))
    analysis.tasks.append({
        "id": task_id,
        "platform": platform,
        "os_version": os_version,
        "state": States.PENDING,
        "score": 0
    })

    return task_values

def create_all(analysis, nodes_tracker):
    tasks = []
    tasknum = 1
    resource_errors = []

    if analysis.settings.machines:
        for machine_name in analysis.settings.machines:
            try:
                tasks.append(_create_task(
                    nodes_tracker, analysis, task_number=tasknum,
                    machine_name=machine_name
                ))
                tasknum += 1
            except MissingResourceError as e:
                resource_errors.append(str(e))
    else:
        for platform in analysis.settings.platforms:
            try:
                tasks.append(_create_task(
                    nodes_tracker, analysis, task_number=tasknum,
                    platform=platform["platform"],
                    os_version=platform["os_version"],
                    machine_tags=platform["tags"],
                    platform_settings=platform.get("settings")
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
        task_dict["created_on"] = analysis.created_on
        task_dict["priority"] = analysis.settings.priority

    # Copy the list of task dicts to allow the changing of data in preparation
    # of db insertion. Normally would be handled by ORM, but is not since
    # we are using a bulk insert here.
    task_rows = copy.deepcopy(tasks)
    for row in task_rows:
        row["machine_tags"] = ",".join(row["machine_tags"])

    ses = db.dbms.session()
    try:
        ses.bulk_insert_mappings(db.Task, task_rows)
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

def merge_errors(task, errors_container):
    if task.errors:
        task.errors.merge_errors(errors_container)
    else:
        task.errors = errors_container

def merge_run_errors(task):
    errpath = TaskPaths.runerr_json(task.id)
    if not os.path.exists(errpath):
        return

    merge_errors(task, Errors.from_file(errpath))

    os.remove(errpath)

def merge_processing_errors(task):
    errpath = TaskPaths.processingerr_json(task.id)
    if not os.path.exists(errpath):
        return

    merge_errors(task, Errors.from_file(errpath))

    os.remove(errpath)

def db_find_state(state):
    ses = db.dbms.session()
    try:
        return ses.query(db.Task).filter_by(state=state)
    finally:
        ses.close()

def exists(task_id):
    return os.path.isfile(TaskPaths.taskjson(task_id))

def has_unfinished_tasks(analysis_id):
    ses = db.dbms.session()
    try:
        count = ses.query(db.Task).filter(
            db.Task.analysis_id==analysis_id,
            db.Task.state.in_(
                [States.PENDING, States.RUNNING, States.PENDING_POST]
            )
        ).count()
        return count > 0
    finally:
        ses.close()

def update_db_row(task_id, **kwargs):
    ses = db.dbms.session()
    try:
        ses.query(db.Task).filter_by(id=task_id).update(kwargs)
        ses.commit()
    finally:
        ses.close()

def write_changes(task):
    if not task.was_updated:
        return

    db_fields = {}
    for field in ("state", "score"):
        if field in task.updated_fields:
            db_fields[field] = task[field]

    task.to_file_safe(TaskPaths.taskjson(task.id))
    if db_fields:
        update_db_row(task.id, **db_fields)
