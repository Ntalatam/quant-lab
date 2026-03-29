"""
POST /api/analytics/compare              — Compare multiple backtest results
POST /api/analytics/monte-carlo/{id}     — Run Monte Carlo simulation
GET  /api/analytics/export/{id}          — Export results as CSV
"""

import csv
import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backtest import BacktestRun
from app.services.analytics import compute_monte_carlo

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
