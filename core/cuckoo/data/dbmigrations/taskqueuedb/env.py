
import logging
from logging.config import fileConfig
from alembic import context

from cuckoo.common.storage import cuckoocwd, Paths
from cuckoo.common.db import DBMS
from cuckoo.taskqueue import AlembicVersion, Base

cuckoocwd.set(context.get_x_argument(as_dictionary=True)["cwd"])

queuedbms = DBMS(
    schema_version=AlembicVersion.SCHEMA_VERSION,
    alembic_version_table=AlembicVersion
)
queuedbms.initialize(
    f"sqlite:///{Paths.queuedb()}", Base,
    migration_check=False, create_tables=False
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.
log = logging.getLogger("alembic")

needs_migration, _, _ = queuedbms.needs_migration()
if not needs_migration:
    log.info("No migration needed for cuckoodb")
    exit(0)

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = queuedbms.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
