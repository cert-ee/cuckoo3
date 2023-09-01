# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import sqlalchemy

from datetime import datetime
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import inspect as sqlalchemy_inspect

from .log import CuckooGlobalLogger

log = CuckooGlobalLogger(__name__)

class DatabaseError(Exception):
    pass

class DatabaseMigrationNeeded(DatabaseError):
    pass

@as_declarative()
class CuckooDBTable:

    def to_dict(self):
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

class AlembicVersion(CuckooDBTable):
    """Database schema version. Used for automatic database migrations."""
    __tablename__ = "alembic_version"

    SCHEMA_VERSION = None

    version_num = sqlalchemy.Column(
        sqlalchemy.String(32), nullable=False, primary_key=True
    )

class Analysis(CuckooDBTable):

    __tablename__ = "analyses"

    id = sqlalchemy.Column(sqlalchemy.String(15), primary_key=True)
    kind = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    created_on = sqlalchemy.Column(
        sqlalchemy.DateTime, nullable=False, default=datetime.utcnow()
    )
    state = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    priority = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)
    score = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)
    location = sqlalchemy.Column(sqlalchemy.String(32), nullable=True)
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

class Task(CuckooDBTable):

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

class Target(CuckooDBTable):

    __tablename__ = "targets"

    analysis_id = sqlalchemy.Column(
        sqlalchemy.String(32), sqlalchemy.ForeignKey("analyses.id"),
        primary_key=True
    )
    category = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    target = sqlalchemy.Column(sqlalchemy.Text(), nullable=False)
    media_type = sqlalchemy.Column(
        sqlalchemy.Text(), nullable=True, default=""
    )
    md5 = sqlalchemy.Column(sqlalchemy.String(32), nullable=True)
    sha1 = sqlalchemy.Column(sqlalchemy.String(40), nullable=True)
    sha256 = sqlalchemy.Column(sqlalchemy.String(64), nullable=True)
    sha512 = sqlalchemy.Column(sqlalchemy.String(128), nullable=True)

class DBMS:

    def __init__(self, schema_version=None, alembic_version_table=None):
        self.initialized = False
        self.session = sessionmaker()
        self.engine = None
        self.connection_string = ""
        self.latest_version = schema_version
        self.alembic_version_table = alembic_version_table

    def needs_migration(self):
        if not self.alembic_version_table:
            return False, "", ""

        if not sqlalchemy_inspect(self.engine).has_table(
                self.alembic_version_table.__tablename__
        ):
            return True, "No version table", self.latest_version

        ses = self.session()
        try:
            v = ses.query(self.alembic_version_table.version_num).first()
            if not v:
                if not self.latest_version:
                    return False, "", ""

                return True, "No version entry", self.latest_version

            return v.version_num != self.latest_version, v, self.latest_version
        finally:
            ses.close()

    def initialize(self, dsn, tablebaseclass, timeout=60,
                   migration_check=True, create_tables=True):
        if self.initialized:
            self.cleanup()

        engine = sqlalchemy.create_engine(
            dsn, poolclass=NullPool, connect_args={"timeout": timeout}
        )
        self.engine = engine
        self.session.configure(bind=engine)

        if migration_check:
            needs_migrate, version, latest_version = self.needs_migration()
            if needs_migrate:
                raise DatabaseMigrationNeeded(
                    f"{engine.url.render_as_string(hide_password=True)}. "
                    f"Found version: '{version}'. "
                    f"Latest version: '{latest_version or ''}'"
                )

        if create_tables:
            try:
                tablebaseclass.metadata.create_all(engine)
            except Exception as e:
                log.error(
                    "Failed to create tables", error=e
                )


        self.initialized = True

    def cleanup(self):
        if self.initialized and self.engine:
            self.engine.dispose()
            self.initialized = False


dbms = DBMS(
    schema_version=AlembicVersion.SCHEMA_VERSION,
    alembic_version_table=AlembicVersion
)
