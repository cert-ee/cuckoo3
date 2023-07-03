# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import hashlib
from threading import RLock

import sqlalchemy
from sqlalchemy.orm import reconstructor
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

from cuckoo.common.db import DBMS
from cuckoo.common.strictcontainer import Route

Base = declarative_base()
TmpBase = declarative_base()

class Ignore(TmpBase):

    __tablename__ = "ignoredhashes"
    __table_args__ = {"prefixes": ["TEMPORARY"]}

    dephash = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)


class AlembicVersion(Base):
    """Database schema version. Used for automatic database migrations."""
    __tablename__ = "alembic_version"

    SCHEMA_VERSION = None

    version_num = sqlalchemy.Column(
        sqlalchemy.String(32), nullable=False, primary_key=True
    )

class QueuedTask(Base):

    __tablename__ = "qeueudtasks"

    id = sqlalchemy.Column(sqlalchemy.String(32), primary_key=True)
    kind = sqlalchemy.Column(sqlalchemy.String(15), nullable=False)
    created_on = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    analysis_id = sqlalchemy.Column(sqlalchemy.String(15), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)
    platform = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    os_version = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    _machine_tags = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    _route = sqlalchemy.Column(sqlalchemy.TEXT, nullable=True)
    dephash = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    scheduled = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._route_str = ""
        self._route_obj = None

    def __repr__(self):
        return f"<Task(id={self.id}," \
               f" platform={self.platform}, os_version={self.os_version}>"

    @reconstructor
    def _init_on_load(self):
        # Sqlalchemy does not call __init__ when creating objects from db
        # data. It does call 'reconstructors'.
        self._route_str = ""
        self._route_obj = None

    @hybrid_property
    def route(self):
        if not self._route:
            return None

        if not self._route_obj:
            self._route_obj = Route.from_string(self._route)

        return self._route_obj

    @route.setter
    def route(self, value):
        if not value:
            return

        if not isinstance(value, Route):
            raise TypeError("Route must be Route instance")

        self._route_str = str(value)
        self._route = value.to_json_string()

    @hybrid_property
    def machine_tags(self):
        if not self._machine_tags:
            return set()

        return set(self._machine_tags.split(","))

    @machine_tags.setter
    def machine_tags(self, value):
        if not isinstance(value, (set, list)):
            raise TypeError("Machine tags must be a list or a set")

        # Ensure the list only has unique values
        if isinstance(value, list):
            value = list(set(value))

        if isinstance(value, set):
            value = list(value)

        # Sort, so that the hash is always calculated on tags that are in the
        # same order.
        value.sort()
        self._machine_tags = ",".join(value)

    def update_dephash(self):
        md5 = hashlib.md5()
        md5.update(
            str((self.platform, self.os_version,
                 self._machine_tags, self._route_str)).encode(errors="replace")
        )
        self.dephash = int(md5.hexdigest()[:12], 16)

class _Counts:

    def __init__(self):
        self.unscheduled = 0


class TaskQuery:

    def __init__(self, session, lock, counts):
        self._ses = session
        self._lock = lock
        self._counts = counts
        self._pending_scheduled_count = 0
        self._ignore_hashes = set()

        # Create temporary table for the storing of hashes to ignore.
        # table should only remain in existing for the current session.
        Ignore.__table__.create(session.connection())

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._ses.commit()
            if self._pending_scheduled_count:
                self._counts.unscheduled -= self._pending_scheduled_count
        finally:
            self._ses.close()
            self._lock.release()

    def ignore_similar_tasks(self, queued_task):
        dephash = queued_task.dephash
        if dephash in self._ignore_hashes:
            return

        self._ignore_hashes.add(dephash)
        self._ses.add(Ignore(dephash=dephash))

    def mark_scheduled(self, queued_task):
        queued_task.scheduled = True
        self._pending_scheduled_count += 1

    def _query_tasks(self, platform=None, os_version=None, limit=5):
        q = self._ses.query(QueuedTask).join(
            Ignore, QueuedTask.dephash == Ignore.dephash, isouter=True
        ).filter(QueuedTask.scheduled==False, Ignore.dephash==None)

        if platform:
            q = q.filter(QueuedTask.platform==platform)
        if os_version:
            q = q.filter(QueuedTask.os_version==os_version)

        return q.order_by(
            QueuedTask.priority.desc(), QueuedTask.created_on.asc()
        ).limit(limit).all()

    def count_unscheduled(self):
        return self._ses.query(
            QueuedTask.id
        ).filter_by(scheduled=False).count()

    def get_unscheduled_tasks(self, platform=None, os_version=None):
        tasks = []
        while True:
            if not tasks:
                tasks = self._query_tasks(
                    platform=platform, os_version=os_version
                )
                if not tasks:
                    return
            try:
                task = tasks.pop(0)
            except IndexError:
                continue

            if task.dephash not in self._ignore_hashes:
                yield task


class TaskQueue:

    def __init__(self, queue_db):
        self._dbms = DBMS(
            schema_version=AlembicVersion.SCHEMA_VERSION,
            alembic_version_table=AlembicVersion
        )
        self._dbms.initialize(f"sqlite:///{queue_db}", tablebaseclass=Base)
        self._lock = RLock()
        self._counts = None
        self._init_counts()

    @property
    def size(self):
        if not self._counts:
            self._init_counts()

        return self._counts.unscheduled

    def _init_counts(self):
        with self._lock:
            self._counts = _Counts()
            with TaskQuery(self._dbms.session(), self._lock,
                           self._counts) as tq:
                self._counts.unscheduled = tq.count_unscheduled()

    def queue_task(self, task_id, kind, created_on, analysis_id, priority,
                   platform, os_version, machine_tags, route):

        with self._lock:
            ses = self._dbms.session()
            try:
                qt = QueuedTask(
                    id=task_id, kind=kind, created_on=created_on,
                    analysis_id=analysis_id, priority=priority,
                    platform=platform, os_version=os_version
                )
                qt.machine_tags = machine_tags
                qt.route = route
                qt.update_dephash()
                ses.add(qt)
                ses.commit()
                self._counts.unscheduled += 1
            finally:
                ses.close()

    def queue_many(self, *task_dicts):
        tasks = []
        for task_dict in task_dicts:
            qt = QueuedTask(
                id=task_dict["id"], kind=task_dict["kind"],
                created_on=task_dict["created_on"],
                analysis_id=task_dict["analysis_id"],
                priority=task_dict["priority"],
                platform=task_dict["platform"],
                os_version=task_dict["os_version"]
            )
            qt.machine_tags = task_dict["machine_tags"]
            qt.route = task_dict["route"]
            qt.update_dephash()
            tasks.append(qt)

        with self._lock:
            ses = self._dbms.session()
            try:
                for t in tasks:
                    ses.add(t)
                ses.commit()
                self._counts.unscheduled += len(tasks)
            finally:
                ses.close()

    def remove(self, *task_ids):
        with self._lock:
            ses = self._dbms.session()
            try:
                ses.connection().execute(
                    QueuedTask.__table__.delete().where(
                        QueuedTask.id.in_(task_ids)
                    )
                )
                ses.commit()
            finally:
                ses.close()

    def get_scheduled(self):
        with self._lock:
            ses = self._dbms.session()
            try:
                return ses.query(QueuedTask).filter_by(scheduled=True).all()
            finally:
                ses.close()

    def mark_unscheduled(self, *task_ids):
        with self._lock:
            ses = self._dbms.session()
            try:
                ses.query(QueuedTask).filter(
                    QueuedTask.id.in_(task_ids)
                ).update({"scheduled": False}, synchronize_session=False)
                ses.commit()
            finally:
                ses.close()

            self._counts.unscheduled += len(task_ids)

    def get_workfinder(self):
        return TaskQuery(
            self._dbms.session(expire_on_commit=False),
            self._lock, self._counts
        )
