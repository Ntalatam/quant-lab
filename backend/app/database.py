from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# Columns added after initial deployment — applied once on startup so existing
# databases pick them up without requiring a full Alembic migration.
_MIGRATIONS = [
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS clean_equity_curve JSON",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS notes VARCHAR(2000)",
    "ALTER TABLE backtest_runs DROP COLUMN IF EXISTS strategy_config_id",
]


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _MIGRATIONS:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists or table not yet created


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
