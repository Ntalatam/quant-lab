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
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS allow_short_selling BOOLEAN DEFAULT FALSE",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS portfolio_construction_model VARCHAR(32) DEFAULT 'equal_weight'",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS portfolio_lookback_days INTEGER DEFAULT 63",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS max_short_position_pct FLOAT DEFAULT 25",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS max_gross_exposure_pct FLOAT DEFAULT 150",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS turnover_limit_pct FLOAT DEFAULT 100",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS max_sector_exposure_pct FLOAT DEFAULT 100",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS short_margin_requirement_pct FLOAT DEFAULT 50",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS short_borrow_rate_bps FLOAT DEFAULT 200",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS short_locate_fee_bps FLOAT DEFAULT 10",
    "ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS short_squeeze_threshold_pct FLOAT DEFAULT 15",
    "ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS position_direction VARCHAR(10) DEFAULT 'LONG'",
    "ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS borrow_cost FLOAT DEFAULT 0",
    "ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS locate_fee FLOAT DEFAULT 0",
    "ALTER TABLE trade_records ADD COLUMN IF NOT EXISTS risk_event VARCHAR(50)",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS allow_short_selling BOOLEAN DEFAULT FALSE",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS portfolio_construction_model VARCHAR(32) DEFAULT 'equal_weight'",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS portfolio_lookback_days INTEGER DEFAULT 63",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS max_gross_exposure_pct FLOAT DEFAULT 150",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS turnover_limit_pct FLOAT DEFAULT 100",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS max_sector_exposure_pct FLOAT DEFAULT 100",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS max_short_position_pct FLOAT DEFAULT 25",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS short_margin_requirement_pct FLOAT DEFAULT 50",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS short_borrow_rate_bps FLOAT DEFAULT 200",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS short_locate_fee_bps FLOAT DEFAULT 10",
    "ALTER TABLE paper_trading_sessions ADD COLUMN IF NOT EXISTS short_squeeze_threshold_pct FLOAT DEFAULT 15",
    "ALTER TABLE paper_trading_positions ADD COLUMN IF NOT EXISTS accrued_borrow_cost FLOAT DEFAULT 0",
    "ALTER TABLE paper_trading_positions ADD COLUMN IF NOT EXISTS accrued_locate_fee FLOAT DEFAULT 0",
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
