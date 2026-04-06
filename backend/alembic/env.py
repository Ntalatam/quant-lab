import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Base.metadata is fully populated
from app.database import Base
from app.models import (  # noqa: F401
    BacktestRun,
    PaperTradingEquityPoint,
    PaperTradingEvent,
    PaperTradingPosition,
    PaperTradingSession,
    PriceData,
    RefreshTokenSession,
    TradeRecord,
    User,
    Workspace,
    WorkspaceMembership,
)

target_metadata = Base.metadata


def _get_url() -> str:
    """Resolve database URL: CLI override > app settings > alembic.ini."""
    # Allow CLI override:  alembic -x db_url=<url> upgrade head
    cli_url = context.get_x_argument(as_dictionary=True).get("db_url")
    if cli_url:
        return cli_url
    # Fall back to app settings (reads from .env / environment)
    from app.config import settings

    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
