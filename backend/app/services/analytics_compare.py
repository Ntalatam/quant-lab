from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    ComparisonResponse,
    MonteCarloResult,
    PortfolioBlendResponse,
)
from app.services.analytics import compute_all_metrics, compute_monte_carlo
from app.services.analytics_backtests import (
    BlendOptimizeMode,
    aligned_equity_frame,
    backtest_equity_series,
    backtest_returns_series,
    benchmark_series,
    build_backtest_export_csv,
    load_backtest_run_or_404,
    load_backtest_runs_or_404,
    resolve_blend_weights,
)


async def build_comparison_response(
    db: AsyncSession,
    backtest_ids: Sequence[str],
    workspace_id: str,
) -> ComparisonResponse:
    if len(backtest_ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to compare")

    runs = await load_backtest_runs_or_404(db, backtest_ids, workspace_id)
    frame = pd.concat([backtest_returns_series(run, name=run.id) for run in runs], axis=1)

    return ComparisonResponse.model_validate(
        {
            "backtests": [
                {
                    "id": run.id,
                    "strategy_id": run.strategy_id,
                    "tickers": run.tickers,
                    "metrics": run.metrics,
                    "equity_curve": run.equity_curve,
                }
                for run in runs
            ],
            "correlation_matrix": frame.corr().values.tolist(),
        }
    )


async def build_monte_carlo_response(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
    *,
    n_simulations: int,
    n_days: int,
) -> MonteCarloResult:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    equity = backtest_equity_series(run)
    returns = equity.pct_change().dropna()

    return MonteCarloResult.model_validate(
        compute_monte_carlo(
            returns,
            n_simulations=n_simulations,
            n_days=n_days,
            initial_value=run.initial_capital,
        )
    )


async def build_backtest_export(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
) -> str:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    return build_backtest_export_csv(run)


async def build_portfolio_blend_response(
    db: AsyncSession,
    backtest_ids: Sequence[str],
    workspace_id: str,
    *,
    weights_in: Sequence[float],
    optimize: BlendOptimizeMode,
) -> PortfolioBlendResponse:
    if len(backtest_ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to blend")

    runs = await load_backtest_runs_or_404(db, backtest_ids, workspace_id)
    aligned_equity = aligned_equity_frame(
        runs,
        normalize_to=1.0,
        column_names=list(range(len(runs))),
    )
    returns = aligned_equity.pct_change().dropna()
    weights = resolve_blend_weights(returns, aligned_equity, optimize, weights_in)

    initial_capital = runs[0].initial_capital
    portfolio_returns = (returns * weights).sum(axis=1)
    portfolio_equity = (1 + portfolio_returns).cumprod() * initial_capital

    benchmark = benchmark_series(runs[0])
    if not benchmark.empty:
        benchmark = benchmark / benchmark.iloc[0] * initial_capital

    metrics = compute_all_metrics(portfolio_equity, benchmark, initial_capital)

    return PortfolioBlendResponse.model_validate(
        {
            "weights": [round(float(weight), 4) for weight in weights],
            "optimize": optimize,
            "equity_curve": [
                {"date": index.date().isoformat(), "value": round(float(value), 2)}
                for index, value in portfolio_equity.items()
            ],
            "metrics": metrics,
            "asset_contributions": [
                {
                    "id": run.id,
                    "strategy_id": run.strategy_id,
                    "tickers": run.tickers,
                    "weight": round(float(weights[index]), 4),
                    "asset_return_pct": round(
                        float(aligned_equity.iloc[-1, index] / aligned_equity.iloc[0, index] - 1)
                        * 100,
                        2,
                    ),
                    "contribution_pct": round(
                        float(aligned_equity.iloc[-1, index] / aligned_equity.iloc[0, index] - 1)
                        * 100
                        * float(weights[index]),
                        2,
                    ),
                }
                for index, run in enumerate(runs)
            ],
        }
    )
