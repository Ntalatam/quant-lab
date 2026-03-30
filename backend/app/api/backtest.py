"""
Backtest API endpoints.

POST   /api/backtest/run      — Run a new backtest
GET    /api/backtest/list      — List all past backtests (summary)
GET    /api/backtest/{id}      — Get full backtest result
DELETE /api/backtest/{id}      — Delete a backtest
POST   /api/backtest/sweep     — Parameter sensitivity sweep
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord
from app.schemas.backtest import BacktestConfig, BacktestSweepConfig, BacktestSweep2DConfig
from app.services.backtest_engine import run_backtest

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
            position_sizing=config.position_sizing,
            max_position_pct=config.max_position_pct,
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
        import uuid

        for trade in result["trades"]:
            tr = TradeRecord(
                id=trade["id"],
                backtest_run_id=result["id"],
                ticker=trade["ticker"],
                side=trade["side"],
                entry_date=trade["entry_date"],
                entry_price=trade["entry_price"],
                exit_date=trade["exit_date"],
                exit_price=trade["exit_price"],
                shares=trade["shares"],
                pnl=trade["pnl"],
                pnl_pct=trade["pnl_pct"],
                commission=trade["commission"],
                slippage=trade["slippage"],
            )
            db.add(tr)

        await db.commit()
        return result

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Backtest failed: {str(e)}")


@router.get("/list")
async def list_backtests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return [
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
    ]


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
            "position_sizing": run.position_sizing,
            "max_position_pct": run.max_position_pct,
            "rebalance_frequency": run.rebalance_frequency,
        },
        "created_at": run.created_at.isoformat() if run.created_at else None,
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
                "entry_date": t.entry_date,
                "entry_price": t.entry_price,
                "exit_date": t.exit_date,
                "exit_price": t.exit_price,
                "shares": t.shares,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "commission": t.commission,
                "slippage": t.slippage,
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


@router.post("/sweep")
async def parameter_sweep(
    config: BacktestSweepConfig, db: AsyncSession = Depends(get_db)
):
    """Run multiple backtests varying one parameter."""
    results = []
    for value in config.sweep_values:
        params = config.base_config.params.copy()
        params[config.sweep_param] = value
        sweep_config = config.base_config.model_copy(update={"params": params})

        try:
            result = await run_backtest(db, sweep_config)
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

    return {
        "sweep_param": config.sweep_param,
        "results": results,
    }


@router.post("/sweep2d")
async def parameter_sweep_2d(
    config: BacktestSweep2DConfig, db: AsyncSession = Depends(get_db)
):
    """Run backtests varying two parameters simultaneously and return a heatmap matrix."""
    cells = []
    for vx in config.values_x:
        row = []
        for vy in config.values_y:
            params = config.base_config.params.copy()
            params[config.param_x] = vx
            params[config.param_y] = vy
            sweep_config = config.base_config.model_copy(update={"params": params})
            try:
                result = await run_backtest(db, sweep_config)
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

    return {
        "param_x": config.param_x,
        "param_y": config.param_y,
        "metric": config.metric,
        "values_x": config.values_x,
        "values_y": config.values_y,
        "cells": cells,
    }
