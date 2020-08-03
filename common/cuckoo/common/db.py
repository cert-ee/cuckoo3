# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import sqlalchemy

from datetime import datetime
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker

@as_declarative()
class Base:
    def to_dict(self):
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

class Analysis(Base):

    __tablename__ = "analyses"

    id = sqlalchemy.Column(sqlalchemy.String(15), primary_key=True)
    kind = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    created_on = sqlalchemy.Column(
        sqlalchemy.DateTime, nullable=False, default=datetime.utcnow()
    )
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)

    def __repr__(self):
        return f"<Analysis(id='{self.id})', state='{self.state}'>"

class Task(Base):

    __tablename__ = "tasks"

    id = sqlalchemy.Column(sqlalchemy.String(32), primary_key=True)
    kind = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    number = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    created_on = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    analysis_id = sqlalchemy.Column(sqlalchemy.String(15), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)
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

    def initialize(self, dsn):
        if self.initialized:
            self.cleanup()

        engine = sqlalchemy.create_engine(dsn)
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
