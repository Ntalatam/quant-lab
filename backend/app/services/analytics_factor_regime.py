from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from scipy.stats import t as t_dist
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import FactorExposureResponse, RegimeAnalysisResponse
from app.services.analytics_backtests import backtest_equity_series, load_backtest_run_or_404
from app.services.analytics_market_data import (
    backtest_date_window,
    load_optional_price_frame,
    load_price_frame_or_422,
)


async def build_regime_analysis(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
) -> RegimeAnalysisResponse:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    start_date, end_date = backtest_date_window(run)
    benchmark_ticker = run.benchmark or "SPY"

    benchmark_frame = await load_price_frame_or_422(
        db,
        benchmark_ticker,
        start_date,
        end_date,
        required_columns=("high", "low", "close"),
        error_detail=f"Could not load {benchmark_ticker} data",
    )

    strategy_returns = backtest_equity_series(run).pct_change().dropna()

    high = benchmark_frame["high"]
    low = benchmark_frame["low"]
    close = benchmark_frame["close"]
    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    dm_plus = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    dm_minus = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    period = 14
    atr = true_range.ewm(span=period, adjust=False).mean()
    di_plus = 100 * pd.Series(dm_plus, index=high.index).ewm(span=period, adjust=False).mean() / atr
    di_minus = (
        100 * pd.Series(dm_minus, index=high.index).ewm(span=period, adjust=False).mean() / atr
    )
    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = dx.ewm(span=period, adjust=False).mean()

    benchmark_returns = close.pct_change().dropna()
    rolling_volatility = benchmark_returns.rolling(21).std() * np.sqrt(252)
    average_volatility = rolling_volatility.mean()

    def classify_regime(index: pd.Timestamp) -> str:
        volatility = rolling_volatility.get(index)
        adx_value = adx.get(index)
        if volatility is None or adx_value is None or pd.isna(volatility) or pd.isna(adx_value):
            return "Neutral"
        if volatility > average_volatility * 1.5:
            return "High Volatility"
        if adx_value > 25:
            return "Trending"
        if adx_value < 15:
            return "Choppy"
        return "Neutral"

    timeline = [
        {
            "date": index.date().isoformat(),
            "regime": classify_regime(index),
            "return": float(value),
        }
        for index, value in strategy_returns.items()
    ]

    regime_groups: dict[str, list[float]] = {}
    for row in timeline:
        regime_groups.setdefault(row["regime"], []).append(row["return"])

    regime_order = ["Trending", "Choppy", "High Volatility", "Neutral"]
    regime_colors = {
        "Trending": "#4488ff",
        "Choppy": "#ffcc44",
        "High Volatility": "#ff4757",
        "Neutral": "#888898",
    }
    regime_stats: list[dict[str, Any]] = []
    for regime in regime_order:
        returns = regime_groups.get(regime, [])
        if not returns:
            continue
        values = np.array(returns)
        annualized_return = float(np.mean(values)) * 252 * 100
        annualized_volatility = (
            float(np.std(values, ddof=1)) * np.sqrt(252) * 100 if len(values) > 1 else 0.0
        )
        regime_stats.append(
            {
                "regime": regime,
                "color": regime_colors[regime],
                "days": len(returns),
                "pct_of_period": round(len(returns) / len(timeline) * 100, 1) if timeline else 0.0,
                "ann_return_pct": round(annualized_return, 2),
                "ann_volatility_pct": round(annualized_volatility, 2),
                "sharpe": round(
                    annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0,
                    3,
                ),
            }
        )

    trending_pct = float(
        next((item["pct_of_period"] for item in regime_stats if item["regime"] == "Trending"), 0.0)
    )
    choppy_pct = float(
        next((item["pct_of_period"] for item in regime_stats if item["regime"] == "Choppy"), 0.0)
    )
    if trending_pct > 40:
        description = (
            "The backtest period was predominantly trending — strategy likely benefits "
            "from directional positions."
        )
    elif choppy_pct > 40:
        description = (
            "The backtest period was predominantly choppy — mean-reversion strategies "
            "should outperform trend-following."
        )
    else:
        description = "Mixed regime environment — strategy performance may vary across sub-periods."

    return RegimeAnalysisResponse.model_validate(
        {
            "timeline": timeline,
            "regime_stats": regime_stats,
            "description": description,
        }
    )


async def build_factor_exposure(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
) -> FactorExposureResponse:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    start_date, end_date = backtest_date_window(run)

    strategy_returns = backtest_equity_series(run).pct_change().dropna()
    factor_tickers = {
        "Market": "SPY",
        "Size": "IWM",
        "Value": "VTV",
        "Momentum": "MTUM",
    }

    factor_prices: dict[str, pd.Series] = {}
    for label, ticker in factor_tickers.items():
        frame = await load_optional_price_frame(
            db,
            ticker,
            start_date,
            end_date,
            required_columns=("adj_close",),
        )
        if frame.empty:
            continue
        factor_prices[label] = pd.Series(
            frame["adj_close"].values,
            index=frame.index,
            name=label,
        )

    spy_prices = factor_prices.get("Market")
    if spy_prices is None:
        raise HTTPException(422, "Could not load market factor data (SPY). Load SPY data first.")

    spy_returns = spy_prices.pct_change()
    factor_returns: dict[str, pd.Series] = {"Market": spy_returns.dropna()}
    for label in ["Size", "Value", "Momentum"]:
        if label not in factor_prices:
            continue
        factor_returns[label] = (factor_prices[label].pct_change() - spy_returns).dropna()

    factor_frame = pd.DataFrame(factor_returns)
    aligned = pd.concat([strategy_returns.rename("Strategy"), factor_frame], axis=1).dropna()
    if len(aligned) < 30:
        raise HTTPException(
            422,
            "Insufficient overlapping data for factor regression (need >=30 days)",
        )

    y = aligned["Strategy"].values
    factor_columns = [column for column in aligned.columns if column != "Strategy"]
    X = np.column_stack([np.ones(len(y)), aligned[factor_columns].values])

    try:
        betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        fitted = X @ betas
        residuals = y - fitted
        n_obs, n_features = X.shape
        sigma2 = np.sum(residuals**2) / max(n_obs - n_features, 1)
        xtx_inv = np.linalg.inv(X.T @ X)
        standard_errors = np.sqrt(np.diag(xtx_inv) * sigma2)
        t_stats = betas / np.where(standard_errors > 0, standard_errors, np.nan)
        p_values = 2 * (1 - t_dist.cdf(np.abs(t_stats), df=max(n_obs - n_features, 1)))
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    except Exception as exc:
        raise HTTPException(500, f"Regression failed: {exc}") from exc

    return FactorExposureResponse.model_validate(
        {
            "alpha_annualized": round(float(betas[0]) * 252 * 100, 4),
            "r_squared": round(float(r_squared), 4),
            "n_obs": int(n_obs),
            "factors": [
                {
                    "name": factor,
                    "beta": round(float(betas[index + 1]), 4),
                    "t_stat": round(float(t_stats[index + 1]), 3),
                    "p_value": round(float(p_values[index + 1]), 4),
                    "significant": bool(p_values[index + 1] < 0.05),
                }
                for index, factor in enumerate(factor_columns)
            ],
        }
    )
