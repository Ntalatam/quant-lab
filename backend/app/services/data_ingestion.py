"""
Data ingestion service.

Fetches OHLCV data from yfinance, validates it, and stores it in PostgreSQL.
Implements gap-fill logic to avoid redundant API calls for already-loaded data.
"""

import yfinance as yf
import pandas as pd
from datetime import date, timedelta

from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_data import PriceData


async def ensure_data_loaded(
    db: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
) -> bool:
    """
    Ensure OHLCV data exists in DB for the full date range.
    Fetches from yfinance only for missing ranges.
    Returns True if data is available, False if fetch failed.
    """
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
            return True

    try:
        df = yf.download(
            ticker,
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            auto_adjust=False,
            progress=False,
        )
        if df.empty:
            return False

        # Flatten MultiIndex columns (happens with single ticker in newer yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close"])
        if len(df) == 0:
            return False

        records = []
        for idx, row in df.iterrows():
            dt = idx.date() if hasattr(idx, "date") else idx
            records.append(
                {
                    "ticker": ticker,
                    "date": dt,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "adj_close": float(row.get("Adj Close", row["Close"])),
                    "volume": int(row["Volume"]),
                }
            )

        if records:
            # Batch into 500-row chunks to stay well under asyncpg's parameter limit
            chunk_size = 500
            for i in range(0, len(records), chunk_size):
                chunk = records[i : i + chunk_size]
                stmt = insert(PriceData).values(chunk)
                stmt = stmt.on_conflict_do_update(
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
                await db.execute(stmt)
            await db.commit()

        return True

    except Exception as e:
        print(f"Failed to fetch data for {ticker}: {e}")
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
    return df
