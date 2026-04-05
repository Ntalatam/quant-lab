from __future__ import annotations

import csv
import io
from collections.abc import Hashable, Sequence
from typing import Any, Literal

import numpy as np
import pandas as pd
from fastapi import HTTPException
from scipy.optimize import minimize
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord

BlendOptimizeMode = Literal["custom", "equal", "max_sharpe", "min_dd"]


async def load_backtest_run_or_404(
    db: AsyncSession,
    backtest_id: str,
    *,
    detail: str = "Backtest not found",
) -> BacktestRun:
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(404, detail)
    return run


async def load_backtest_runs_or_404(
    db: AsyncSession,
    backtest_ids: Sequence[str],
) -> list[BacktestRun]:
    runs: list[BacktestRun] = []
    for backtest_id in backtest_ids:
        runs.append(
            await load_backtest_run_or_404(
                db,
                backtest_id,
                detail=f"Backtest {backtest_id} not found",
            )
        )
    return runs


async def load_backtest_trades(
    db: AsyncSession,
    backtest_id: str,
) -> list[TradeRecord]:
    result = await db.execute(
        select(TradeRecord)
        .where(TradeRecord.backtest_run_id == backtest_id)
        .order_by(TradeRecord.entry_date.asc(), TradeRecord.ticker.asc(), TradeRecord.id.asc())
    )
    return list(result.scalars().all())


def curve_to_series(
    curve: Sequence[dict[str, Any]],
    *,
    normalize_to: float | None = None,
    name: Hashable | None = None,
) -> pd.Series:
    if not curve:
        return pd.Series(dtype=float, name=name)

    series = pd.Series(
        [point["value"] for point in curve],
        index=pd.to_datetime([point["date"] for point in curve]),
        dtype=float,
        name=name,
    )
    if normalize_to is not None and not series.empty:
        series = series / float(series.iloc[0]) * normalize_to
        series = series.rename(name)
    return series


def backtest_equity_series(
    run: BacktestRun,
    *,
    normalize_to: float | None = None,
    name: Hashable | None = None,
) -> pd.Series:
    return curve_to_series(run.equity_curve, normalize_to=normalize_to, name=name)


def backtest_returns_series(
    run: BacktestRun,
    *,
    name: Hashable | None = None,
) -> pd.Series:
    return backtest_equity_series(run, name=name).pct_change().dropna()


def benchmark_series(
    run: BacktestRun,
    *,
    scale_to: float | None = None,
) -> pd.Series:
    return curve_to_series(run.benchmark_curve, normalize_to=scale_to)


def aligned_equity_frame(
    runs: Sequence[BacktestRun],
    *,
    normalize_to: float | None = None,
    column_names: Sequence[Hashable] | None = None,
) -> pd.DataFrame:
    names = column_names or [run.id for run in runs]
    series = [
        backtest_equity_series(run, normalize_to=normalize_to, name=name)
        for run, name in zip(runs, names, strict=True)
    ]
    return pd.concat(series, axis=1).ffill().dropna()


def build_backtest_export_csv(run: BacktestRun) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== Configuration ==="])
    writer.writerow(["strategy", run.strategy_id])
    writer.writerow(["tickers", ", ".join(run.tickers)])
    writer.writerow(["period", f"{run.start_date} to {run.end_date}"])
    writer.writerow(["initial_capital", run.initial_capital])
    writer.writerow([])

    writer.writerow(["=== Performance Metrics ==="])
    for key, value in run.metrics.items():
        writer.writerow([key, value])

    writer.writerow([])
    writer.writerow(["=== Equity Curve ==="])
    writer.writerow(["date", "equity"])
    for point in run.equity_curve:
        writer.writerow([point["date"], point["value"]])

    writer.writerow([])
    writer.writerow(["=== Monthly Returns ==="])
    writer.writerow(["year", "month", "return_pct"])
    for monthly_return in run.monthly_returns:
        writer.writerow(
            [monthly_return["year"], monthly_return["month"], monthly_return["return_pct"]]
        )

    return output.getvalue()


def resolve_blend_weights(
    returns: pd.DataFrame,
    equities: pd.DataFrame,
    optimize: BlendOptimizeMode,
    provided_weights: Sequence[float],
) -> np.ndarray:
    n_assets = returns.shape[1]

    if optimize == "equal":
        return np.full(n_assets, 1.0 / n_assets)
    if optimize == "max_sharpe":
        return _max_sharpe_weights(returns)
    if optimize == "min_dd":
        return _min_drawdown_weights(equities)

    weights = np.array(provided_weights[:n_assets], dtype=float)
    if len(weights) < n_assets:
        weights = np.pad(weights, (0, n_assets - len(weights)))

    total = float(weights.sum())
    if np.isclose(total, 0.0):
        return np.full(n_assets, 1.0 / n_assets)
    return weights / total


def _max_sharpe_weights(returns: pd.DataFrame) -> np.ndarray:
    n_assets = returns.shape[1]
    mean_returns = returns.mean() * 252
    covariance = returns.cov() * 252

    def neg_sharpe(weights: np.ndarray) -> float:
        portfolio_return = float(np.dot(weights, mean_returns))
        portfolio_vol = float(np.sqrt(np.dot(weights, np.dot(covariance.values, weights))))
        return -portfolio_return / portfolio_vol if portfolio_vol > 0 else 0.0

    constraints = [{"type": "eq", "fun": lambda weights: np.sum(weights) - 1}]
    bounds = [(0.0, 1.0)] * n_assets
    initial_guess = np.full(n_assets, 1.0 / n_assets)
    result = minimize(
        neg_sharpe,
        initial_guess,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return _normalized_weights(result.x if result.success else initial_guess)


def _min_drawdown_weights(equities: pd.DataFrame) -> np.ndarray:
    n_assets = equities.shape[1]

    def max_drawdown(weights: np.ndarray) -> float:
        portfolio_equity = (equities * weights).sum(axis=1)
        rolling_max = portfolio_equity.expanding().max()
        drawdown = (portfolio_equity - rolling_max) / rolling_max
        return float(-drawdown.min())

    constraints = [{"type": "eq", "fun": lambda weights: np.sum(weights) - 1}]
    bounds = [(0.0, 1.0)] * n_assets
    initial_guess = np.full(n_assets, 1.0 / n_assets)
    result = minimize(
        max_drawdown,
        initial_guess,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return _normalized_weights(result.x if result.success else initial_guess)


def _normalized_weights(weights: np.ndarray) -> np.ndarray:
    clipped = np.clip(weights, 0.0, None)
    total = float(clipped.sum())
    if np.isclose(total, 0.0):
        return np.full(len(clipped), 1.0 / len(clipped))
    return clipped / total
