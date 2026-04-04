"""
Backtest API endpoints.

POST   /api/backtest/run      — Run a new backtest
GET    /api/backtest/list      — List all past backtests (summary)
GET    /api/backtest/{id}      — Get full backtest result
DELETE /api/backtest/{id}      — Delete a backtest
POST   /api/backtest/sweep     — Parameter sensitivity sweep
"""

import json
import time
from collections.abc import Sequence
from datetime import date
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord
from app.observability import elapsed_ms, get_logger
from app.schemas.backtest import (
    BacktestConfig,
    BacktestListResponse,
    BacktestResultResponse,
    BacktestSweep2DConfig,
    BacktestSweepConfig,
    BayesOptConfig,
    BayesOptResponse,
    LineageResponse,
    LineageTagRequest,
    LineageTagResponse,
    NotesUpdateRequest,
    NotesUpdateResponse,
    Sweep2DResponse,
    SweepResponse,
    WalkForwardRequest,
    WalkForwardResponse,
)
from app.schemas.common import DeleteResponse, ErrorResponse
from app.services.backtest_engine import run_backtest
from app.services.walk_forward import run_walk_forward

router = APIRouter(prefix="/backtest", tags=["backtest"])
logger = get_logger(__name__)


def serialize_backtest_run(run: BacktestRun, trades: Sequence[TradeRecord]) -> dict[str, Any]:
    return {
        "id": run.id,
        "config": {
            "strategy_id": run.strategy_id,
            "params": run.strategy_params,
            "tickers": run.tickers,
            "benchmark": run.benchmark,
            "start_date": run.start_date,
            "end_date": run.end_date,
            "initial_capital": run.initial_capital,
            "slippage_bps": run.slippage_bps,
            "commission_per_share": run.commission_per_share,
            "market_impact_model": run.market_impact_model or "almgren_chriss",
            "max_volume_participation_pct": run.max_volume_participation_pct or 5,
            "position_sizing": run.position_sizing,
            "portfolio_construction_model": run.portfolio_construction_model or run.position_sizing,
            "portfolio_lookback_days": run.portfolio_lookback_days or 63,
            "max_position_pct": run.max_position_pct,
            "max_gross_exposure_pct": run.max_gross_exposure_pct or 150,
            "turnover_limit_pct": run.turnover_limit_pct or 100,
            "max_sector_exposure_pct": run.max_sector_exposure_pct or 100,
            "allow_short_selling": run.allow_short_selling,
            "max_short_position_pct": run.max_short_position_pct,
            "short_margin_requirement_pct": run.short_margin_requirement_pct,
            "short_borrow_rate_bps": run.short_borrow_rate_bps,
            "short_locate_fee_bps": run.short_locate_fee_bps,
            "short_squeeze_threshold_pct": run.short_squeeze_threshold_pct,
            "rebalance_frequency": run.rebalance_frequency,
        },
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "notes": run.notes or "",
        "lineage_tag": run.lineage_tag,
        "version": run.version,
        "parent_id": run.parent_id,
        "equity_curve": run.equity_curve,
        "clean_equity_curve": run.clean_equity_curve or [],
        "benchmark_curve": run.benchmark_curve,
        "drawdown_series": run.drawdown_series,
        "rolling_sharpe": run.rolling_sharpe,
        "rolling_volatility": run.rolling_volatility,
        "metrics": run.metrics,
        "benchmark_metrics": run.benchmark_metrics,
        "trades": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "side": t.side,
                "position_direction": t.position_direction,
                "entry_date": t.entry_date,
                "entry_price": t.entry_price,
                "exit_date": t.exit_date,
                "exit_price": t.exit_price,
                "shares": t.shares,
                "requested_shares": t.requested_shares,
                "unfilled_shares": t.unfilled_shares,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "commission": t.commission,
                "slippage": t.slippage,
                "spread_cost": t.spread_cost,
                "market_impact_cost": t.market_impact_cost,
                "timing_cost": t.timing_cost,
                "opportunity_cost": t.opportunity_cost,
                "participation_rate_pct": t.participation_rate_pct,
                "implementation_shortfall": t.implementation_shortfall,
                "borrow_cost": t.borrow_cost,
                "locate_fee": t.locate_fee,
                "risk_event": t.risk_event,
            }
            for t in trades
        ],
        "monthly_returns": run.monthly_returns,
    }


@router.post(
    "/run",
    response_model=BacktestResultResponse,
    summary="Run and persist a backtest",
    description=(
        "Executes a full historical simulation, persists the run and trade log, "
        "and returns the full tear-sheet payload used by the frontend."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Backtest configuration was invalid.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Backtest execution failed unexpectedly.",
        },
    },
)
async def execute_backtest(config: BacktestConfig, db: AsyncSession = Depends(get_db)):
    start_time = time.perf_counter()
    log = logger.bind(
        strategy_id=config.strategy_id,
        tickers=config.tickers,
        benchmark=config.benchmark,
    )
    try:
        result = await run_backtest(db, config)

        # Persist to database
        run = BacktestRun(
            id=result["id"],
            strategy_id=config.strategy_id,
            strategy_params=config.params,
            tickers=config.tickers,
            benchmark=config.benchmark,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            slippage_bps=config.slippage_bps,
            commission_per_share=config.commission_per_share,
            market_impact_model=config.market_impact_model,
            max_volume_participation_pct=config.max_volume_participation_pct,
            position_sizing=config.position_sizing,
            portfolio_construction_model=config.portfolio_construction_model,
            portfolio_lookback_days=config.portfolio_lookback_days,
            max_position_pct=config.max_position_pct,
            max_gross_exposure_pct=config.max_gross_exposure_pct,
            turnover_limit_pct=config.turnover_limit_pct,
            max_sector_exposure_pct=config.max_sector_exposure_pct,
            allow_short_selling=config.allow_short_selling,
            max_short_position_pct=config.max_short_position_pct,
            short_margin_requirement_pct=config.short_margin_requirement_pct,
            short_borrow_rate_bps=config.short_borrow_rate_bps,
            short_locate_fee_bps=config.short_locate_fee_bps,
            short_squeeze_threshold_pct=config.short_squeeze_threshold_pct,
            rebalance_frequency=config.rebalance_frequency,
            equity_curve=result["equity_curve"],
            clean_equity_curve=result.get("clean_equity_curve", []),
            benchmark_curve=result["benchmark_curve"],
            drawdown_series=result["drawdown_series"],
            rolling_sharpe=result["rolling_sharpe"],
            rolling_volatility=result["rolling_volatility"],
            monthly_returns=result["monthly_returns"],
            metrics=result["metrics"],
            benchmark_metrics=result["benchmark_metrics"],
        )
        db.add(run)

        persisted_trades: list[TradeRecord] = []
        # Persist trades
        for trade in result["trades"]:
            tr = TradeRecord(
                id=trade["id"],
                backtest_run_id=result["id"],
                ticker=trade["ticker"],
                side=trade["side"],
                position_direction=trade["position_direction"],
                entry_date=trade["entry_date"],
                entry_price=trade["entry_price"],
                exit_date=trade["exit_date"],
                exit_price=trade["exit_price"],
                shares=trade["shares"],
                requested_shares=trade["requested_shares"],
                unfilled_shares=trade["unfilled_shares"],
                pnl=trade["pnl"],
                pnl_pct=trade["pnl_pct"],
                commission=trade["commission"],
                slippage=trade["slippage"],
                spread_cost=trade["spread_cost"],
                market_impact_cost=trade["market_impact_cost"],
                timing_cost=trade["timing_cost"],
                opportunity_cost=trade["opportunity_cost"],
                participation_rate_pct=trade["participation_rate_pct"],
                implementation_shortfall=trade["implementation_shortfall"],
                borrow_cost=trade["borrow_cost"],
                locate_fee=trade["locate_fee"],
                risk_event=trade["risk_event"],
            )
            db.add(tr)
            persisted_trades.append(tr)

        await db.commit()
        await db.refresh(run)
        log.info(
            "backtest.persisted",
            duration_ms=elapsed_ms(start_time),
            backtest_id=result["id"],
            trade_count=len(result["trades"]),
        )
        return serialize_backtest_run(run, persisted_trades)

    except ValueError as e:
        log.warning(
            "backtest.rejected",
            duration_ms=elapsed_ms(start_time),
            error=str(e),
        )
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception(
            "backtest.request_failed",
            duration_ms=elapsed_ms(start_time),
            error=str(e),
        )
        raise HTTPException(500, f"Backtest failed: {str(e)}")


@router.get(
    "/list",
    response_model=BacktestListResponse,
    summary="List saved backtests",
    description="Returns paginated saved backtests with summary performance metrics for result-table views.",
)
async def list_backtests(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    total = await db.scalar(select(func.count()).select_from(BacktestRun))
    result = await db.execute(
        select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit).offset(offset)
    )
    runs = result.scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "strategy_name": r.strategy_id,
                "tickers": r.tickers,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "total_return_pct": r.metrics.get("total_return_pct", 0),
                "sharpe_ratio": r.metrics.get("sharpe_ratio", 0),
                "max_drawdown_pct": r.metrics.get("max_drawdown_pct", 0),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "lineage_tag": r.lineage_tag,
                "version": r.version,
            }
            for r in runs
        ],
        "total": total or 0,
    }


@router.get(
    "/{backtest_id}",
    response_model=BacktestResultResponse,
    summary="Read a saved backtest",
    description="Returns the persisted run configuration, analytics series, trade log, and notes for one backtest.",
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def get_backtest(backtest_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    # Load trades
    trades_result = await db.execute(
        select(TradeRecord).where(TradeRecord.backtest_run_id == backtest_id)
    )
    trades = trades_result.scalars().all()

    return serialize_backtest_run(run, trades)


@router.delete(
    "/{backtest_id}",
    response_model=DeleteResponse,
    summary="Delete a saved backtest",
    description="Deletes the saved backtest record and its persisted trade ledger.",
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def delete_backtest(backtest_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    await db.execute(delete(TradeRecord).where(TradeRecord.backtest_run_id == backtest_id))
    await db.execute(delete(BacktestRun).where(BacktestRun.id == backtest_id))
    await db.commit()
    return {"status": "deleted"}


@router.patch(
    "/{backtest_id}/notes",
    response_model=NotesUpdateResponse,
    summary="Update analyst notes for a backtest",
    description="Stores free-form notes used to annotate a saved backtest result.",
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def update_notes(
    backtest_id: str,
    payload: NotesUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")
    run.notes = payload.notes[:2000]
    await db.commit()
    return {"id": backtest_id, "notes": run.notes}


@router.post(
    "/sweep",
    response_model=SweepResponse,
    summary="Run a one-dimensional parameter sweep",
    description=(
        "Runs the same base configuration multiple times while varying a single "
        "parameter and returns summary metrics for each value."
    ),
    responses={400: {"model": ErrorResponse, "description": "Sweep request was invalid."}},
)
async def parameter_sweep(config: BacktestSweepConfig, db: AsyncSession = Depends(get_db)):
    """Run multiple backtests varying one parameter (parallelized)."""
    import asyncio

    from app.database import async_session as _async_session
    from app.services.data_ingestion import ensure_data_loaded as _ensure
    from app.services.parallel import run_in_thread_pool, run_parallel_sweeps

    # Pre-load data so individual runs skip DB checks
    start = date.fromisoformat(config.base_config.start_date)
    end = date.fromisoformat(config.base_config.end_date)
    for t in set(config.base_config.tickers + [config.base_config.benchmark]):
        await _ensure(db, t, start, end)

    def _make_task(value):
        def _task():
            params = config.base_config.params.copy()
            params[config.sweep_param] = value
            sweep_config = config.base_config.model_copy(update={"params": params})
            try:

                async def _run():
                    async with _async_session() as sess:
                        return await run_backtest(sess, sweep_config)

                result = asyncio.run(_run())
                return {
                    "param_value": value,
                    "sharpe_ratio": result["metrics"]["sharpe_ratio"],
                    "total_return_pct": result["metrics"]["total_return_pct"],
                    "max_drawdown_pct": result["metrics"]["max_drawdown_pct"],
                    "cagr_pct": result["metrics"]["cagr_pct"],
                }
            except Exception as e:
                return {"param_value": value, "error": str(e)}

        return _task

    tasks = [_make_task(v) for v in config.sweep_values]
    results = await run_in_thread_pool(lambda: run_parallel_sweeps(tasks), max_workers=1)

    return {
        "sweep_param": config.sweep_param,
        "results": results,
    }


@router.post(
    "/sweep2d",
    response_model=Sweep2DResponse,
    summary="Run a two-dimensional parameter sweep",
    description=(
        "Evaluates a backtest across a 2D grid of parameter combinations and "
        "returns a heatmap-ready response."
    ),
    responses={400: {"model": ErrorResponse, "description": "Sweep request was invalid."}},
)
async def parameter_sweep_2d(config: BacktestSweep2DConfig, db: AsyncSession = Depends(get_db)):
    """Run backtests varying two parameters simultaneously (parallelized)."""
    import asyncio

    from app.database import async_session as _async_session
    from app.services.data_ingestion import ensure_data_loaded as _ensure
    from app.services.parallel import run_in_thread_pool, run_parallel_sweeps

    # Pre-load data
    start = date.fromisoformat(config.base_config.start_date)
    end = date.fromisoformat(config.base_config.end_date)
    for t in set(config.base_config.tickers + [config.base_config.benchmark]):
        await _ensure(db, t, start, end)

    # Flatten 2D grid into parallel tasks
    grid_coords = [(vx, vy) for vx in config.values_x for vy in config.values_y]

    def _make_task(vx, vy):
        def _task():
            params = config.base_config.params.copy()
            params[config.param_x] = vx
            params[config.param_y] = vy
            sweep_config = config.base_config.model_copy(update={"params": params})
            try:

                async def _run():
                    async with _async_session() as sess:
                        return await run_backtest(sess, sweep_config)

                result = asyncio.run(_run())
                metric_val = result["metrics"].get(config.metric)
                return {
                    "x": vx,
                    "y": vy,
                    "value": metric_val,
                    "total_return_pct": result["metrics"].get("total_return_pct"),
                    "max_drawdown_pct": result["metrics"].get("max_drawdown_pct"),
                }
            except Exception as e:
                return {"x": vx, "y": vy, "value": None, "error": str(e)}

        return _task

    tasks = [_make_task(vx, vy) for vx, vy in grid_coords]
    flat_results = await run_in_thread_pool(lambda: run_parallel_sweeps(tasks), max_workers=1)

    # Reshape flat results back into 2D grid
    n_y = len(config.values_y)
    cells = [flat_results[i : i + n_y] for i in range(0, len(flat_results), n_y)]

    return {
        "param_x": config.param_x,
        "param_y": config.param_y,
        "metric": config.metric,
        "values_x": config.values_x,
        "values_y": config.values_y,
        "cells": cells,
    }


@router.post(
    "/walk-forward",
    response_model=WalkForwardResponse,
    summary="Run walk-forward analysis",
    description=(
        "Splits a strategy into rolling in-sample and out-of-sample windows to "
        "measure robustness and out-of-sample degradation."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Walk-forward request was invalid.",
        },
        500: {"model": ErrorResponse, "description": "Walk-forward execution failed."},
    },
)
async def walk_forward(
    payload: WalkForwardRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run walk-forward analysis on an existing backtest config."""
    import asyncio

    from app.database import async_session as _async_session
    from app.services.data_ingestion import ensure_data_loaded as _ensure
    from app.services.parallel import run_in_thread_pool

    config = payload.config
    n_folds = int(payload.n_folds)
    train_pct = float(payload.train_pct)
    if not (2 <= n_folds <= 10):
        raise HTTPException(400, "n_folds must be 2–10")
    if not (0.5 <= train_pct <= 0.9):
        raise HTTPException(400, "train_pct must be 0.5–0.9")

    # Pre-load data
    start = date.fromisoformat(config.start_date)
    end = date.fromisoformat(config.end_date)
    for t in set(config.tickers + [config.benchmark]):
        await _ensure(db, t, start, end)

    def _run_wfa():
        async def _inner():
            async with _async_session() as sess:
                return await run_walk_forward(sess, config, n_folds=n_folds, train_pct=train_pct)

        return asyncio.run(_inner())

    try:
        return await run_in_thread_pool(_run_wfa)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Walk-forward failed: {e}")


@router.post(
    "/optimize",
    response_model=BayesOptResponse,
    summary="Run Bayesian parameter optimization",
    description=(
        "Uses Optuna to evaluate full backtests across parameter ranges and "
        "returns the best parameter set plus the complete trial log."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Optimization request was invalid.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Optimization could not be completed.",
        },
    },
)
async def bayesian_optimize(
    config: BayesOptConfig,
    db: AsyncSession = Depends(get_db),
):
    """
    Run Bayesian optimization (Optuna) to find the best parameter combination.

    Runs up to n_trials evaluations, each a full backtest, and returns the
    best parameter set along with all trial results for visualization.
    """
    try:
        import optuna

        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        raise HTTPException(500, "optuna is not installed. Run: pip install optuna")

    from app.database import async_session as _async_session

    # Pre-load price data once so individual trials skip ensure_data_loaded DB checks
    from app.services.data_ingestion import ensure_data_loaded

    start = date.fromisoformat(config.base_config.start_date)
    end = date.fromisoformat(config.base_config.end_date)
    all_tickers = list(set(config.base_config.tickers + [config.base_config.benchmark]))
    for ticker in all_tickers:
        loaded = await ensure_data_loaded(db, ticker, start, end)
        if not loaded:
            raise HTTPException(400, f"Could not load data for {ticker}")

    trials_log: list[dict[str, Any]] = []

    def objective(trial: Any) -> float:
        import asyncio

        params = dict(config.base_config.params)
        for spec in config.param_specs:
            if spec.type == "int":
                step = int(spec.step) if spec.step else 1
                params[spec.name] = trial.suggest_int(
                    spec.name, int(spec.low), int(spec.high), step=step
                )
            else:
                params[spec.name] = trial.suggest_float(
                    spec.name, spec.low, spec.high, step=spec.step
                )

        trial_config = config.base_config.model_copy(update={"params": params})

        async def _run():
            async with _async_session() as sess:
                return await run_backtest(sess, trial_config)

        try:
            result = asyncio.run(_run())
        except Exception:
            return float("-inf") if config.maximize else float("inf")

        metric_val = result["metrics"].get(config.metric)
        if metric_val is None:
            return float("-inf") if config.maximize else float("inf")

        trials_log.append(
            {
                "trial": trial.number,
                "params": dict(params),
                "value": float(metric_val),
            }
        )
        return float(metric_val) if config.maximize else -float(metric_val)

    # Optuna must run sync — use thread pool to avoid blocking event loop
    from app.services.parallel import run_in_thread_pool

    def run_study():
        direction = "maximize" if config.maximize else "minimize"
        study = optuna.create_study(direction=direction)
        study.optimize(objective, n_trials=min(config.n_trials, 50), n_jobs=1)
        return study

    study = await run_in_thread_pool(run_study)

    best_params = dict(config.base_config.params)
    best_params.update(study.best_params)
    best_value = study.best_value if config.maximize else -study.best_value

    # Sort trials for visualization
    trials_sorted = sorted(trials_log, key=lambda t: int(t["trial"]))

    return {
        "best_params": best_params,
        "best_value": round(float(best_value), 4),
        "metric": config.metric,
        "n_trials": len(trials_sorted),
        "trials": trials_sorted,
        "param_specs": [s.model_dump() for s in config.param_specs],
    }


# ── Versioning / lineage ──────────────────────────────────────────────────


@router.patch(
    "/{backtest_id}/lineage",
    response_model=LineageTagResponse,
    summary="Tag a backtest with a lineage identifier",
    description=(
        "Assigns a lineage tag and optional parent link. "
        "The version number is auto-incremented within the lineage."
    ),
    responses={404: {"model": ErrorResponse}},
)
async def set_lineage(
    backtest_id: str,
    payload: LineageTagRequest,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    # Compute next version in this lineage
    existing = await db.execute(
        select(BacktestRun.version)
        .where(BacktestRun.lineage_tag == payload.lineage_tag)
        .order_by(BacktestRun.version.desc())
    )
    max_ver = existing.scalar()
    next_ver = (max_ver or 0) + 1

    run.lineage_tag = payload.lineage_tag
    run.version = next_ver
    run.parent_id = payload.parent_id
    await db.commit()

    return {
        "id": run.id,
        "lineage_tag": run.lineage_tag,
        "version": run.version,
        "parent_id": run.parent_id,
    }


@router.get(
    "/lineage/{tag}",
    response_model=LineageResponse,
    summary="Get full lineage for a tag",
    description=(
        "Returns all backtests tagged with the given lineage, ordered by version, "
        "with parameter diffs showing what changed between iterations."
    ),
    responses={404: {"model": ErrorResponse}},
)
async def get_lineage(
    tag: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BacktestRun)
        .where(BacktestRun.lineage_tag == tag)
        .order_by(BacktestRun.version.asc())
    )
    runs = result.scalars().all()

    if not runs:
        raise HTTPException(404, f"No backtests found for lineage '{tag}'")

    entries = []
    prev_params: dict | None = None
    for run in runs:
        params = run.strategy_params or {}
        diffs = []
        if prev_params is not None:
            all_keys = set(list(prev_params.keys()) + list(params.keys()))
            for k in sorted(all_keys):
                old = prev_params.get(k)
                new = params.get(k)
                if old != new:
                    diffs.append({"key": k, "old_value": old, "new_value": new})

        entries.append(
            {
                "id": run.id,
                "version": run.version,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "notes": run.notes or "",
                "strategy_id": run.strategy_id,
                "tickers": run.tickers,
                "params": params,
                "sharpe_ratio": run.metrics.get("sharpe_ratio", 0),
                "total_return_pct": run.metrics.get("total_return_pct", 0),
                "max_drawdown_pct": run.metrics.get("max_drawdown_pct", 0),
                "param_diffs": diffs,
            }
        )
        prev_params = params

    return {"lineage_tag": tag, "entries": entries}


@router.get(
    "/lineages",
    summary="List all lineage tags",
    description="Returns all distinct lineage tags and how many versions each has.",
)
async def list_lineages(
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    result = await db.execute(
        select(
            BacktestRun.lineage_tag,
            func.count(BacktestRun.id).label("count"),
            func.max(BacktestRun.version).label("max_version"),
        )
        .where(BacktestRun.lineage_tag.isnot(None))
        .group_by(BacktestRun.lineage_tag)
        .order_by(func.max(BacktestRun.created_at).desc())
    )
    rows = result.all()
    return {
        "lineages": [
            {"tag": row.lineage_tag, "count": row.count, "max_version": row.max_version}
            for row in rows
        ]
    }


@router.websocket("/ws")
async def backtest_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time backtest progress streaming.

    Protocol:
      Client → sends JSON BacktestConfig
      Server → streams {"type":"progress","bar":N,"total":M,"date":"...","equity":V,"pct":0..1}
      Server → sends   {"type":"complete","id":"...","result":{...}} on success
      Server → sends   {"type":"error","message":"..."} on failure
    """
    from app.database import async_session

    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        config_data = json.loads(raw)
        config = BacktestConfig(**config_data)

        async def on_progress(bar_num: int, total_bars: int, date_str: str, equity: float):
            pct = round(bar_num / total_bars, 4) if total_bars else 0
            try:
                await websocket.send_json(
                    {
                        "type": "progress",
                        "bar": bar_num,
                        "total": total_bars,
                        "date": date_str,
                        "equity": round(equity, 2),
                        "pct": pct,
                    }
                )
            except Exception:
                pass  # client disconnected mid-run

        async with async_session() as db:
            try:
                result = await run_backtest(db, config, on_progress=on_progress)

                # Persist result (same logic as HTTP endpoint)
                run = BacktestRun(
                    id=result["id"],
                    strategy_id=config.strategy_id,
                    strategy_params=config.params,
                    tickers=config.tickers,
                    benchmark=config.benchmark,
                    start_date=config.start_date,
                    end_date=config.end_date,
                    initial_capital=config.initial_capital,
                    slippage_bps=config.slippage_bps,
                    commission_per_share=config.commission_per_share,
                    market_impact_model=config.market_impact_model,
                    max_volume_participation_pct=config.max_volume_participation_pct,
                    position_sizing=config.position_sizing,
                    portfolio_construction_model=config.portfolio_construction_model,
                    portfolio_lookback_days=config.portfolio_lookback_days,
                    max_position_pct=config.max_position_pct,
                    max_gross_exposure_pct=config.max_gross_exposure_pct,
                    turnover_limit_pct=config.turnover_limit_pct,
                    max_sector_exposure_pct=config.max_sector_exposure_pct,
                    allow_short_selling=config.allow_short_selling,
                    max_short_position_pct=config.max_short_position_pct,
                    short_margin_requirement_pct=config.short_margin_requirement_pct,
                    short_borrow_rate_bps=config.short_borrow_rate_bps,
                    short_locate_fee_bps=config.short_locate_fee_bps,
                    short_squeeze_threshold_pct=config.short_squeeze_threshold_pct,
                    rebalance_frequency=config.rebalance_frequency,
                    equity_curve=result["equity_curve"],
                    clean_equity_curve=result.get("clean_equity_curve", []),
                    benchmark_curve=result["benchmark_curve"],
                    drawdown_series=result["drawdown_series"],
                    rolling_sharpe=result["rolling_sharpe"],
                    rolling_volatility=result["rolling_volatility"],
                    monthly_returns=result["monthly_returns"],
                    metrics=result["metrics"],
                    benchmark_metrics=result["benchmark_metrics"],
                )
                db.add(run)
                for trade in result["trades"]:
                    tr = TradeRecord(
                        id=trade["id"],
                        backtest_run_id=result["id"],
                        ticker=trade["ticker"],
                        side=trade["side"],
                        position_direction=trade["position_direction"],
                        entry_date=trade["entry_date"],
                        entry_price=trade["entry_price"],
                        exit_date=trade["exit_date"],
                        exit_price=trade["exit_price"],
                        shares=trade["shares"],
                        requested_shares=trade["requested_shares"],
                        unfilled_shares=trade["unfilled_shares"],
                        pnl=trade["pnl"],
                        pnl_pct=trade["pnl_pct"],
                        commission=trade["commission"],
                        slippage=trade["slippage"],
                        spread_cost=trade["spread_cost"],
                        market_impact_cost=trade["market_impact_cost"],
                        timing_cost=trade["timing_cost"],
                        opportunity_cost=trade["opportunity_cost"],
                        participation_rate_pct=trade["participation_rate_pct"],
                        implementation_shortfall=trade["implementation_shortfall"],
                        borrow_cost=trade["borrow_cost"],
                        locate_fee=trade["locate_fee"],
                        risk_event=trade["risk_event"],
                    )
                    db.add(tr)
                await db.commit()

                await websocket.send_json({"type": "complete", "id": result["id"]})
            except ValueError as e:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"Backtest failed: {e}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
