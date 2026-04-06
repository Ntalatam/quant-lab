"""Data ingestion service backed by configurable market-data providers."""

import time
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_data import PriceData
from app.observability import elapsed_ms, get_logger
from app.services.providers.helpers import normalize_price_history
from app.services.providers.registry import get_provider_registry

logger = get_logger(__name__)


def _build_sqlite_price_data_upsert(records: list[dict]) -> Any:
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    stmt = sqlite_insert(PriceData).values(records)
    return stmt.on_conflict_do_update(
        index_elements=["ticker", "date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adj_close": stmt.excluded.adj_close,
            "volume": stmt.excluded.volume,
        },
    )


def _build_postgres_price_data_upsert(records: list[dict]) -> Any:
    from sqlalchemy.dialects.postgresql import insert as postgresql_insert

    stmt = postgresql_insert(PriceData).values(records)
    return stmt.on_conflict_do_update(
        constraint="uq_ticker_date",
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adj_close": stmt.excluded.adj_close,
            "volume": stmt.excluded.volume,
        },
    )


def _build_price_data_upsert_statement(db: AsyncSession, records: list[dict]) -> Any:
    dialect_name = db.bind.dialect.name if db.bind is not None else ""

    if dialect_name == "sqlite":
        return _build_sqlite_price_data_upsert(records)

    if dialect_name == "postgresql":
        return _build_postgres_price_data_upsert(records)

    raise RuntimeError(f"Unsupported database dialect for price-data upserts: {dialect_name}")


async def ensure_data_loaded(
    db: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
) -> bool:
    """
    Ensure OHLCV data exists in DB for the full date range.
    Fetches from the configured market-data provider only for missing ranges.
    Returns True if data is available, False if fetch failed.
    """
    start_time = time.perf_counter()
    log = logger.bind(
        ticker=ticker,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    existing = await db.execute(
        select(PriceData.date)
        .where(
            and_(
                PriceData.ticker == ticker,
                PriceData.date >= start_date,
                PriceData.date <= end_date,
            )
        )
        .order_by(PriceData.date)
    )
    existing_dates = {row[0] for row in existing.fetchall()}

    if existing_dates:
        all_days = pd.bdate_range(start_date, end_date)
        expected = {d.date() for d in all_days}
        missing = expected - existing_dates
        if len(missing) / max(len(expected), 1) < 0.05:
            log.debug(
                "market_data.cache_hit",
                duration_ms=elapsed_ms(start_time),
                loaded_days=len(existing_dates),
                expected_days=len(expected),
            )
            return True

    try:
        fetch_start = time.perf_counter()
        df = await get_provider_registry().market_data.fetch_price_history(
            ticker,
            start_date,
            end_date,
        )
        df = normalize_price_history(df)
        if df.empty:
            log.warning(
                "market_data.fetch_empty",
                duration_ms=elapsed_ms(fetch_start),
            )
            return False

        records = []
        for idx, row in df.iterrows():
            dt = idx.date() if hasattr(idx, "date") else idx
            records.append(
                {
                    "ticker": ticker,
                    "date": dt,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "adj_close": float(row["adj_close"]),
                    "volume": int(row["volume"]),
                }
            )

        if records:
            # Batch into 500-row chunks to stay well under asyncpg's parameter limit
            chunk_size = 500
            for i in range(0, len(records), chunk_size):
                chunk = records[i : i + chunk_size]
                stmt = _build_price_data_upsert_statement(db, chunk)
                await db.execute(stmt)
            await db.commit()

        log.info(
            "market_data.fetch_completed",
            duration_ms=elapsed_ms(fetch_start),
            rows=len(records),
            source="provider",
        )
        return True

    except Exception as e:
        log.exception(
            "market_data.fetch_failed",
            duration_ms=elapsed_ms(start_time),
            error=str(e),
        )
        return False


async def get_price_dataframe(
    db: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Retrieve OHLCV data from the database as a pandas DataFrame.
    Indexed by date, sorted ascending.
    """
    start_time = time.perf_counter()
    result = await db.execute(
        select(PriceData)
        .where(
            and_(
                PriceData.ticker == ticker,
                PriceData.date >= start_date,
                PriceData.date <= end_date,
            )
        )
        .order_by(PriceData.date)
    )
    rows = result.scalars().all()

    data = [
        {
            "date": r.date,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "adj_close": r.adj_close,
            "volume": r.volume,
        }
        for r in rows
    ]

    df = pd.DataFrame(data)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
    logger.debug(
        "market_data.frame_loaded",
        ticker=ticker,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        rows=len(df),
        duration_ms=elapsed_ms(start_time),
    )
    return df
