import time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.observability import elapsed_ms, get_logger

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Initialize database using Alembic migrations.

    Runs ``alembic upgrade head`` programmatically so every startup applies
    any pending migrations.  Falls back to ``Base.metadata.create_all`` only
    when Alembic is unavailable (e.g. minimal test environments).
    """
    start_time = time.perf_counter()
    try:
        from alembic.config import Config

        from alembic import command

        alembic_cfg = Config("alembic.ini")
        # Override the URL so it always matches the app settings
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        # Alembic's command.upgrade is synchronous.  Run it in the default
        # executor so it doesn't block the event loop.
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
        logger.info(
            "database.initialized",
            method="alembic",
            duration_ms=elapsed_ms(start_time),
        )
    except Exception as exc:
        # Alembic not configured or migrations dir missing — fall back to
        # metadata create_all (safe for SQLite dev/test databases).
        logger.warning(
            "database.alembic_fallback",
            error=str(exc),
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(
            "database.initialized",
            method="metadata_create_all",
            duration_ms=elapsed_ms(start_time),
        )


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
