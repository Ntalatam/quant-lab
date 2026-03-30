"""
POST /api/analytics/compare              — Compare multiple backtest results
POST /api/analytics/monte-carlo/{id}     — Run Monte Carlo simulation
GET  /api/analytics/export/{id}          — Export results as CSV
POST /api/analytics/portfolio-blend      — Blend multiple backtests with weights
"""

import csv
import io

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backtest import BacktestRun
from app.services.analytics import compute_monte_carlo, compute_all_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/compare")
async def compare_backtests(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    ids = payload.get("backtest_ids", [])
    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to compare")

    results = []
    for bid in ids:
        r = await db.execute(select(BacktestRun).where(BacktestRun.id == bid))
        run = r.scalar_one_or_none()
        if not run:
            raise HTTPException(404, f"Backtest {bid} not found")
        results.append(run)

    # Correlation matrix from equity curves
    curves = {}
    for run in results:
        series = (
            pd.Series(
                [p["value"] for p in run.equity_curve],
                index=pd.to_datetime([p["date"] for p in run.equity_curve]),
            )
            .pct_change()
            .dropna()
        )
        curves[run.id] = series

    df = pd.DataFrame(curves)
    corr = df.corr().values.tolist()

    return {
        "backtests": [
            {
                "id": r.id,
                "strategy_id": r.strategy_id,
                "tickers": r.tickers,
                "metrics": r.metrics,
                "equity_curve": r.equity_curve,
            }
            for r in results
        ],
        "correlation_matrix": corr,
    }


@router.post("/monte-carlo/{backtest_id}")
async def monte_carlo(
    backtest_id: str,
    n_simulations: int = Query(1000, ge=100, le=10000),
    n_days: int = Query(252, ge=30, le=1260),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    equity = pd.Series(
        [p["value"] for p in run.equity_curve],
        index=pd.to_datetime([p["date"] for p in run.equity_curve]),
    )
    returns = equity.pct_change().dropna()

    result = compute_monte_carlo(
        returns,
        n_simulations=n_simulations,
        n_days=n_days,
        initial_value=run.initial_capital,
    )
    return result


@router.get("/export/{backtest_id}")
async def export_results(
    backtest_id: str,
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    if format == "csv":
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
        for pt in run.equity_curve:
            writer.writerow([pt["date"], pt["value"]])

        writer.writerow([])
        writer.writerow(["=== Monthly Returns ==="])
        writer.writerow(["year", "month", "return_pct"])
        for mr in run.monthly_returns:
            writer.writerow([mr["year"], mr["month"], mr["return_pct"]])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=backtest_{backtest_id[:8]}.csv"
                )
            },
        )

    raise HTTPException(501, "Only CSV export is currently supported")


@router.post("/portfolio-blend")
async def portfolio_blend(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Blend multiple backtests by weights and return portfolio equity + metrics.

    payload: { backtest_ids: [...], weights: [...], optimize: "equal"|"max_sharpe"|"min_dd" }
    """
    ids = payload.get("backtest_ids", [])
    weights_in = payload.get("weights", [])
    optimize = payload.get("optimize", "custom")

    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to blend")

    runs = []
    for bid in ids:
        r = await db.execute(select(BacktestRun).where(BacktestRun.id == bid))
        run = r.scalar_one_or_none()
        if not run:
            raise HTTPException(404, f"Backtest {bid} not found")
        runs.append(run)

    # Align equity curves to common dates
    series_list = []
    for run in runs:
        s = pd.Series(
            [p["value"] for p in run.equity_curve],
            index=pd.to_datetime([p["date"] for p in run.equity_curve]),
        )
        # Normalize to 1.0 start
        s = s / s.iloc[0]
        series_list.append(s)

    df = pd.concat(series_list, axis=1).ffill().dropna()
    df.columns = list(range(len(runs)))

    returns = df.pct_change().dropna()
    n = len(runs)

    if optimize == "equal":
        weights = np.array([1.0 / n] * n)
    elif optimize == "max_sharpe":
        weights = _max_sharpe_weights(returns)
    elif optimize == "min_dd":
        weights = _min_dd_weights(returns, df)
    else:
        # Use provided weights, normalize to sum to 1
        w = np.array(weights_in[:n], dtype=float)
        if w.sum() == 0:
            w = np.ones(n) / n
        weights = w / w.sum()

    # Compute portfolio equity curve
    initial_capital = runs[0].initial_capital
    portfolio_returns = (returns * weights).sum(axis=1)
    portfolio_equity = (1 + portfolio_returns).cumprod() * initial_capital

    # Align index back to dates
    equity_curve = [
        {"date": idx.date().isoformat(), "value": round(float(v), 2)}
        for idx, v in portfolio_equity.items()
    ]

    # Metrics on portfolio
    bench_series = pd.Series(
        [p["value"] for p in runs[0].benchmark_curve],
        index=pd.to_datetime([p["date"] for p in runs[0].benchmark_curve]),
    ) if runs[0].benchmark_curve else pd.Series(dtype=float)
    # Normalize benchmark to same scale
    if not bench_series.empty:
        bench_series = bench_series / bench_series.iloc[0] * initial_capital

    metrics = compute_all_metrics(portfolio_equity, bench_series, initial_capital)

    # Per-asset contribution (return attribution)
    total_return = float(portfolio_equity.iloc[-1] / portfolio_equity.iloc[0] - 1) * 100
    asset_contribs = []
    for i, run in enumerate(runs):
        asset_return = float(df.iloc[-1, i] / df.iloc[0, i] - 1) * 100
        asset_contribs.append({
            "id": run.id,
            "strategy_id": run.strategy_id,
            "tickers": run.tickers,
            "weight": round(float(weights[i]), 4),
            "asset_return_pct": round(asset_return, 2),
            "contribution_pct": round(asset_return * float(weights[i]), 2),
        })

    return {
        "weights": [round(float(w), 4) for w in weights],
        "optimize": optimize,
        "equity_curve": equity_curve,
        "metrics": metrics,
        "asset_contributions": asset_contribs,
    }


def _max_sharpe_weights(returns: pd.DataFrame) -> np.ndarray:
    """Find weights maximizing Sharpe ratio via scipy optimization."""
    from scipy.optimize import minimize

    n = returns.shape[1]
    mean_ret = returns.mean() * 252
    cov = returns.cov() * 252

    def neg_sharpe(w):
        port_ret = np.dot(w, mean_ret)
        port_vol = np.sqrt(np.dot(w, np.dot(cov.values, w)))
        return -port_ret / port_vol if port_vol > 0 else 0

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n
    result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    w = result.x
    return w / w.sum()


def _min_dd_weights(returns: pd.DataFrame, df: pd.DataFrame) -> np.ndarray:
    """Find weights minimizing maximum portfolio drawdown."""
    from scipy.optimize import minimize

    n = returns.shape[1]

    def max_dd(w):
        port_equity = (df * w).sum(axis=1)
        roll_max = port_equity.expanding().max()
        dd = (port_equity - roll_max) / roll_max
        return float(dd.min())  # most negative value = worst drawdown

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n
    result = minimize(max_dd, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    w = result.x
    return w / w.sum()
