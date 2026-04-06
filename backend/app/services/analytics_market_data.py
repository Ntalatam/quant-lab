from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestRun
from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe


def backtest_date_window(run: BacktestRun) -> tuple[date, date]:
    return date.fromisoformat(run.start_date), date.fromisoformat(run.end_date)


async def load_price_frame_or_422(
    db: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    required_columns: Sequence[str] = (),
    error_detail: str | None = None,
) -> pd.DataFrame:
    detail = error_detail or f"Could not load data for {ticker}"
    loaded = await ensure_data_loaded(db, ticker, start_date, end_date)
    if not loaded:
        raise HTTPException(422, detail)

    frame = await get_price_dataframe(db, ticker, start_date, end_date)
    if frame.empty:
        raise HTTPException(422, detail)

    missing = [column for column in required_columns if column not in frame]
    if missing:
        raise HTTPException(422, detail)

    return frame


async def load_optional_price_frame(
    db: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    required_columns: Sequence[str] = (),
) -> pd.DataFrame:
    try:
        loaded = await ensure_data_loaded(db, ticker, start_date, end_date)
        if not loaded:
            return pd.DataFrame()

        frame = await get_price_dataframe(db, ticker, start_date, end_date)
    except Exception:
        return pd.DataFrame()

    if frame.empty:
        return pd.DataFrame()

    missing = [column for column in required_columns if column not in frame]
    if missing:
        return pd.DataFrame()

    return frame


async def load_price_series_map(
    db: AsyncSession,
    tickers: Sequence[str],
    start_date: date,
    end_date: date,
    *,
    column: str,
) -> tuple[dict[str, pd.Series], list[str]]:
    prices: dict[str, pd.Series] = {}
    failed: list[str] = []

    for ticker in tickers:
        frame = await load_optional_price_frame(
            db,
            ticker,
            start_date,
            end_date,
            required_columns=(column,),
        )
        if frame.empty:
            failed.append(ticker)
            continue
        prices[ticker] = frame[column]

    return prices, failed
