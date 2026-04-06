from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    CorrelationRequest,
    CorrelationResponse,
    SpreadRequest,
    SpreadResponse,
)
from app.services.analytics_market_data import load_price_frame_or_422, load_price_series_map
from app.services.cointegration import (
    compute_correlation_matrix,
    compute_spread,
    discover_pairs,
    engle_granger_test,
)


async def build_correlation_response(
    db: AsyncSession,
    payload: CorrelationRequest,
) -> CorrelationResponse:
    start_date = date.fromisoformat(payload.start_date)
    end_date = date.fromisoformat(payload.end_date)
    prices, failed = await load_price_series_map(
        db,
        payload.tickers,
        start_date,
        end_date,
        column="close",
    )

    if failed:
        raise HTTPException(422, f"Could not load data for: {', '.join(failed)}")
    if len(prices) < 2:
        raise HTTPException(400, "Need at least 2 tickers with available data")

    try:
        correlation = compute_correlation_matrix(prices, payload.rolling_window)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return CorrelationResponse.model_validate(
        {
            "tickers": correlation["tickers"],
            "static_matrix": correlation["static_matrix"],
            "rolling_correlations": correlation["rolling_correlations"],
            "discovered_pairs": discover_pairs(prices, payload.max_pairs),
        }
    )


async def build_spread_response(
    db: AsyncSession,
    payload: SpreadRequest,
) -> SpreadResponse:
    start_date = date.fromisoformat(payload.start_date)
    end_date = date.fromisoformat(payload.end_date)

    frame_a = await load_price_frame_or_422(
        db,
        payload.ticker_a,
        start_date,
        end_date,
        required_columns=("close",),
        error_detail=f"Could not load data for {payload.ticker_a}",
    )
    frame_b = await load_price_frame_or_422(
        db,
        payload.ticker_b,
        start_date,
        end_date,
        required_columns=("close",),
        error_detail=f"Could not load data for {payload.ticker_b}",
    )

    combined = pd.DataFrame(
        {
            payload.ticker_a: frame_a["close"],
            payload.ticker_b: frame_b["close"],
        }
    ).dropna()
    if len(combined) < payload.lookback:
        raise HTTPException(
            400,
            f"Only {len(combined)} overlapping days — need at least {payload.lookback}",
        )

    series_a = combined[payload.ticker_a]
    series_b = combined[payload.ticker_b]
    spread = compute_spread(series_a, series_b, payload.lookback)
    cointegration = engle_granger_test(series_a, series_b)

    return SpreadResponse.model_validate(
        {
            "ticker_a": payload.ticker_a,
            "ticker_b": payload.ticker_b,
            "spread_series": spread["spread_series"],
            "zscore_series": spread["zscore_series"],
            "half_life_days": spread["half_life_days"],
            "current_zscore": spread["current_zscore"],
            "spread_mean": spread["spread_mean"],
            "spread_std": spread["spread_std"],
            "cointegration": {
                "ticker_a": payload.ticker_a,
                "ticker_b": payload.ticker_b,
                "adf_statistic": cointegration["adf_statistic"],
                "adf_pvalue": cointegration["adf_pvalue"],
                "cointegrated": cointegration["cointegrated"],
                "beta": cointegration["beta"],
                "half_life_days": spread["half_life_days"],
                "current_zscore": spread["current_zscore"],
                "spread_std": spread["spread_std"],
            },
        }
    )
