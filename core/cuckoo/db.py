# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import sqlalchemy

from datetime import datetime
from sqlalchemy.ext import declarative
from sqlalchemy.orm import sessionmaker

Base = declarative.declarative_base()

class AnalysisStates(object):

    PENDING_IDENTIFICATION = "pending_identification"
    NO_SELECTED = "no_selected"
    FATAL_ERROR = "fatal_error"
    WAITING_MANUAL = "waiting_manual"
    PENDING_PRE = "pending_pre"
    COMPLETED_PRE = "completed_pre"

class TaskStates(object):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    REPORTED = "reported"

class Analysis(Base):

    __tablename__ = "analyses"

    id = sqlalchemy.Column(sqlalchemy.String(15), primary_key=True)
    created_on = sqlalchemy.Column(
        sqlalchemy.DateTime, nullable=False, default=datetime.utcnow()
    )
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1)

    def __repr__(self):
        return f"<Analysis(id='{self.id})', state='{self.state}'>"

class Task(Base):

    __tablename__ = "tasks"

    number = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=False
    )
    analysis = sqlalchemy.Column(sqlalchemy.String(15), primary_key=True)
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    machine = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    machine_tags = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)

    def __repr__(self):
        return f"<Task(number={self.number}, analysis={self.analysis})>"

class _DBMS(object):

    def __init__(self):
        self.initialized = False
        self.session = sessionmaker()
        self.engine = None
        self.connection_string = ""

    def initialize(self, db_path):
        if self.initialized:
            self.cleanup()

        engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        self.engine = engine
        self.session.configure(bind=engine)

    def cleanup(self):
        if self.initialized and self.engine:
            self.engine.dispose()

    def __del__(self):
        self.cleanup()

dbms = _DBMS()


def set_analysis_state(analysis_id, state):
    ses = dbms.session()
    try:
        ses.query(Analysis).filter_by(id=analysis_id).update({"state": state})
        ses.commit()
    finally:
        ses.close()

def set_task_state(analysis_id, task_id, state):
    ses = dbms.session()
    try:
        ses.query(Task).filter(
            Task.number==task_id, Task.analysis==analysis_id
        ).update({"state": state})
        ses.commit()
    finally:
        ses.close()