"""
Backtest API endpoints.

POST   /api/backtest/run      — Run a new backtest
GET    /api/backtest/list      — List all past backtests (summary)
GET    /api/backtest/{id}      — Get full backtest result
DELETE /api/backtest/{id}      — Delete a backtest
POST   /api/backtest/sweep     — Parameter sensitivity sweep
"""

import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord
from app.schemas.backtest import BacktestConfig, BacktestSweepConfig, BacktestSweep2DConfig, BayesOptConfig
from app.services.backtest_engine import run_backtest
from app.services.walk_forward import run_walk_forward

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run")
async def execute_backtest(
    config: BacktestConfig, db: AsyncSession = Depends(get_db)
):
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

        await db.commit()
        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Backtest failed: {str(e)}")


@router.get("/list")
async def list_backtests(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    total = await db.scalar(select(func.count()).select_from(BacktestRun))
    result = await db.execute(
        select(BacktestRun)
        .order_by(BacktestRun.created_at.desc())
        .limit(limit)
        .offset(offset)
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
            }
            for r in runs
        ],
        "total": total or 0,
    }


@router.get("/{backtest_id}")
async def get_backtest(backtest_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    # Load trades
    trades_result = await db.execute(
        select(TradeRecord).where(TradeRecord.backtest_run_id == backtest_id)
    )
    trades = trades_result.scalars().all()

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
            "portfolio_construction_model": run.portfolio_construction_model
            or run.position_sizing,
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


@router.delete("/{backtest_id}")
async def delete_backtest(backtest_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    await db.execute(
        delete(TradeRecord).where(TradeRecord.backtest_run_id == backtest_id)
    )
    await db.execute(
        delete(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    await db.commit()
    return {"status": "deleted"}


@router.patch("/{backtest_id}/notes")
async def update_notes(
    backtest_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")
    run.notes = payload.get("notes", "")[:2000]
    await db.commit()
    return {"id": backtest_id, "notes": run.notes}


@router.post("/sweep")
async def parameter_sweep(
    config: BacktestSweepConfig, db: AsyncSession = Depends(get_db)
):
    """Run multiple backtests varying one parameter."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.database import async_session as _async_session
    from app.services.data_ingestion import ensure_data_loaded as _ensure

    # Pre-load data so individual runs skip DB checks
    start = date.fromisoformat(config.base_config.start_date)
    end = date.fromisoformat(config.base_config.end_date)
    for t in set(config.base_config.tickers + [config.base_config.benchmark]):
        await _ensure(db, t, start, end)

    def _run_sweep():
        results = []
        for value in config.sweep_values:
            params = config.base_config.params.copy()
            params[config.sweep_param] = value
            sweep_config = config.base_config.model_copy(update={"params": params})

            try:
                async def _run(cfg=sweep_config):
                    async with _async_session() as sess:
                        return await run_backtest(sess, cfg)
                result = asyncio.run(_run())
                results.append(
                    {
                        "param_value": value,
                        "sharpe_ratio": result["metrics"]["sharpe_ratio"],
                        "total_return_pct": result["metrics"]["total_return_pct"],
                        "max_drawdown_pct": result["metrics"]["max_drawdown_pct"],
                        "cagr_pct": result["metrics"]["cagr_pct"],
                    }
                )
            except Exception as e:
                results.append({"param_value": value, "error": str(e)})
        return results

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        results = await loop.run_in_executor(pool, _run_sweep)

    return {
        "sweep_param": config.sweep_param,
        "results": results,
    }


@router.post("/sweep2d")
async def parameter_sweep_2d(
    config: BacktestSweep2DConfig, db: AsyncSession = Depends(get_db)
):
    """Run backtests varying two parameters simultaneously and return a heatmap matrix."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.database import async_session as _async_session
    from app.services.data_ingestion import ensure_data_loaded as _ensure

    # Pre-load data
    start = date.fromisoformat(config.base_config.start_date)
    end = date.fromisoformat(config.base_config.end_date)
    for t in set(config.base_config.tickers + [config.base_config.benchmark]):
        await _ensure(db, t, start, end)

    def _run_sweep2d():
        cells = []
        for vx in config.values_x:
            row = []
            for vy in config.values_y:
                params = config.base_config.params.copy()
                params[config.param_x] = vx
                params[config.param_y] = vy
                sweep_config = config.base_config.model_copy(update={"params": params})
                try:
                    async def _run(cfg=sweep_config):
                        async with _async_session() as sess:
                            return await run_backtest(sess, cfg)
                    result = asyncio.run(_run())
                    metric_val = result["metrics"].get(config.metric)
                    row.append(
                        {
                            "x": vx,
                            "y": vy,
                            "value": metric_val,
                            "total_return_pct": result["metrics"].get("total_return_pct"),
                            "max_drawdown_pct": result["metrics"].get("max_drawdown_pct"),
                        }
                    )
                except Exception as e:
                    row.append({"x": vx, "y": vy, "value": None, "error": str(e)})
            cells.append(row)
        return cells

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        cells = await loop.run_in_executor(pool, _run_sweep2d)

    return {
        "param_x": config.param_x,
        "param_y": config.param_y,
        "metric": config.metric,
        "values_x": config.values_x,
        "values_y": config.values_y,
        "cells": cells,
    }


@router.post("/walk-forward")
async def walk_forward(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Run walk-forward analysis on an existing backtest config."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.database import async_session as _async_session
    from app.services.data_ingestion import ensure_data_loaded as _ensure

    config = BacktestConfig(**payload["config"])
    n_folds   = int(payload.get("n_folds",   5))
    train_pct = float(payload.get("train_pct", 0.7))
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
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, _run_wfa)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Walk-forward failed: {e}")


@router.post("/optimize")
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

    trials_log = []

    def objective(trial: "optuna.Trial") -> float:  # type: ignore[name-defined]
        import asyncio

        params = dict(config.base_config.params)
        for spec in config.param_specs:
            if spec.type == "int":
                step = int(spec.step) if spec.step else 1
                params[spec.name] = trial.suggest_int(spec.name, int(spec.low), int(spec.high), step=step)
            else:
                params[spec.name] = trial.suggest_float(spec.name, spec.low, spec.high, step=spec.step)

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

        trials_log.append({
            "trial": trial.number,
            "params": dict(params),
            "value": float(metric_val),
        })
        return float(metric_val) if config.maximize else -float(metric_val)

    # Optuna must run sync — use thread pool to avoid blocking event loop
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def run_study():
        direction = "maximize" if config.maximize else "minimize"
        study = optuna.create_study(direction=direction)
        study.optimize(objective, n_trials=min(config.n_trials, 50), n_jobs=1)
        return study

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        study = await loop.run_in_executor(pool, run_study)

    best_params = dict(config.base_config.params)
    best_params.update(study.best_params)
    best_value = study.best_value if config.maximize else -study.best_value

    # Sort trials for visualization
    trials_sorted = sorted(trials_log, key=lambda t: t["trial"])

    return {
        "best_params": best_params,
        "best_value": round(float(best_value), 4),
        "metric": config.metric,
        "n_trials": len(trials_sorted),
        "trials": trials_sorted,
        "param_specs": [s.model_dump() for s in config.param_specs],
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
                await websocket.send_json({
                    "type":   "progress",
                    "bar":    bar_num,
                    "total":  total_bars,
                    "date":   date_str,
                    "equity": round(equity, 2),
                    "pct":    pct,
                })
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
