import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from alembic import context

# add project src/ to Python path.Ensures Alembic can import:
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # G:\projects\dashnotesystem
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from core.database.base import Base
from config import settings
from auth import models as auth_models  # noqa: F401 - impoprted for side effect
from workspaces import models as workspace_models  # noqa: F401 imported for side effect

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic what to track
target_metadata = Base.metadata

# Convert async URL to sync URL for Alembic
# postgresql+asyncpg:// -> postgresql:// (uses psycopg2)
# or postgresql+asyncpg:// -> postgresql+psycopg2://
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql+asyncpg://"):
    # Convert asyncpg URL to standard PostgreSQL URL (uses psycopg2)
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
elif database_url.startswith("postgresql://"):
    # Already a sync URL, keep it
    pass
else:
    # Try to convert other async formats
    database_url = database_url.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create a synchronous engine for Alembic
    connectable = create_engine(
        database_url,
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()