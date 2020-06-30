# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import sqlalchemy

from datetime import datetime
from sqlalchemy.ext import declarative
from sqlalchemy.orm import sessionmaker

Base = declarative.declarative_base()

class AnalysisStates:

    PENDING_IDENTIFICATION = "pending_identification"
    NO_SELECTED = "no_selected"
    FATAL_ERROR = "fatal_error"
    WAITING_MANUAL = "waiting_manual"
    PENDING_PRE = "pending_pre"
    COMPLETED_PRE = "completed_pre"

class AnalysisKinds:
    STANDARD = "standard"

class TaskStates:
    PENDING = "pending"
    RUNNING = "running"
    FATAL_ERROR = "fatal_error"
    PENDING_POST = "pending_post"
    REPORTED = "reported"

class Analysis(Base):

    __tablename__ = "analyses"

    id = sqlalchemy.Column(sqlalchemy.String(15), primary_key=True)
    kind = sqlalchemy.Column(
        sqlalchemy.String(32), default=AnalysisKinds.STANDARD
    )
    created_on = sqlalchemy.Column(
        sqlalchemy.DateTime, nullable=False, default=datetime.utcnow()
    )
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1)

    def __repr__(self):
        return f"<Analysis(id='{self.id})', state='{self.state}'>"

class Task(Base):

    __tablename__ = "tasks"

    id = sqlalchemy.Column(sqlalchemy.String(32), primary_key=True)
    kind = sqlalchemy.Column(
        sqlalchemy.String(32), default=AnalysisKinds.STANDARD
    )
    number = sqlalchemy.Column(
        sqlalchemy.Integer, autoincrement=False, nullable=False
    )
    created_on = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    analysis_id = sqlalchemy.Column(sqlalchemy.String(15), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    machine = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    machine_tags = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    platform = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    os_version = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)

    def __repr__(self):
        return f"<Task(id={self.id}, number={self.number}," \
               f" analysis={self.analysis_id})>"

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
