# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import sqlalchemy

from datetime import datetime
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.hybrid import hybrid_property

@as_declarative()
class CuckooDBDTable:
    def to_dict(self):
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

class Analysis(CuckooDBDTable):

    __tablename__ = "analyses"

    id = sqlalchemy.Column(sqlalchemy.String(15), primary_key=True)
    kind = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    created_on = sqlalchemy.Column(
        sqlalchemy.DateTime, nullable=False, default=datetime.utcnow()
    )
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)
    score = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)
    target = relationship("Target", uselist=False, lazy="selectin")

    def __repr__(self):
        return f"<Analysis(id='{self.id})', state='{self.state}'>"

    def to_dict(self):
        d = super().to_dict()
        if self.target:
            d["target"] = self.target.to_dict()
        else:
            d["target"] = {}

        return d


class Task(CuckooDBDTable):

    __tablename__ = "tasks"

    id = sqlalchemy.Column(sqlalchemy.String(32), primary_key=True)
    kind = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    number = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    created_on = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    analysis_id = sqlalchemy.Column(sqlalchemy.String(15), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    machine = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    _machine_tags = sqlalchemy.Column(
        "machine_tags", sqlalchemy.String(255), nullable=True
    )
    platform = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    os_version = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    score = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<Task(id={self.id}, number={self.number}," \
               f" analysis={self.analysis_id})>"

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

        self._machine_tags = ",".join(value)

class Target(CuckooDBDTable):

    __tablename__ = "targets"

    analysis_id = sqlalchemy.Column(
        sqlalchemy.String(32), sqlalchemy.ForeignKey("analyses.id"),
        primary_key=True
    )
    category = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    target = sqlalchemy.Column(sqlalchemy.Text(), nullable=False)
    media_type = sqlalchemy.Column(sqlalchemy.Text(), nullable=True)
    md5 = sqlalchemy.Column(sqlalchemy.String(32), nullable=True)
    sha1 = sqlalchemy.Column(sqlalchemy.String(40), nullable=True)
    sha256 = sqlalchemy.Column(sqlalchemy.String(64), nullable=True)
    sha512 = sqlalchemy.Column(sqlalchemy.String(128), nullable=True)

class DBMS(object):

    def __init__(self):
        self.initialized = False
        self.session = sessionmaker()
        self.engine = None
        self.connection_string = ""

    def initialize(self, dsn, tablebaseclass):
        if self.initialized:
            self.cleanup()

        engine = sqlalchemy.create_engine(
            dsn, poolclass=NullPool, connect_args={"timeout": 60}
        )
        tablebaseclass.metadata.create_all(engine)

        self.engine = engine
        self.session.configure(bind=engine)
        self.initialized = True

    def cleanup(self):
        if self.initialized and self.engine:
            self.engine.dispose()
            self.initialized = False

dbms = DBMS()
