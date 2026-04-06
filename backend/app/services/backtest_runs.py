from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord
from app.schemas.backtest import BacktestConfig


def _build_backtest_run(config: BacktestConfig, result: dict[str, Any]) -> BacktestRun:
    return BacktestRun(
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


def _build_trade_record(backtest_run_id: str, trade: dict[str, Any]) -> TradeRecord:
    return TradeRecord(
        id=trade["id"],
        backtest_run_id=backtest_run_id,
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


async def persist_backtest_result(
    db: AsyncSession,
    config: BacktestConfig,
    result: dict[str, Any],
    *,
    workspace_id: str,
    created_by_user_id: str,
) -> tuple[BacktestRun, list[TradeRecord]]:
    run = _build_backtest_run(config, result)
    run.workspace_id = workspace_id
    run.created_by_user_id = created_by_user_id
    trades = [_build_trade_record(result["id"], trade) for trade in result["trades"]]

    db.add(run)
    for trade in trades:
        db.add(trade)

    await db.commit()
    detail = await load_backtest_detail(db, result["id"])
    if detail is None:
        raise RuntimeError(f"Persisted backtest {result['id']} could not be reloaded")
    return detail


async def load_backtest_detail(
    db: AsyncSession,
    backtest_id: str,
    *,
    workspace_id: str | None = None,
) -> tuple[BacktestRun, list[TradeRecord]] | None:
    query = select(BacktestRun).where(BacktestRun.id == backtest_id)
    if workspace_id is not None:
        query = query.where(BacktestRun.workspace_id == workspace_id)
    run_result = await db.execute(query)
    run = run_result.scalar_one_or_none()
    if run is None:
        return None

    trades_result = await db.execute(
        select(TradeRecord)
        .where(TradeRecord.backtest_run_id == backtest_id)
        .order_by(TradeRecord.entry_date.asc(), TradeRecord.ticker.asc(), TradeRecord.id.asc())
    )
    return run, list(trades_result.scalars().all())


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
                "id": trade.id,
                "ticker": trade.ticker,
                "side": trade.side,
                "position_direction": trade.position_direction,
                "entry_date": trade.entry_date,
                "entry_price": trade.entry_price,
                "exit_date": trade.exit_date,
                "exit_price": trade.exit_price,
                "shares": trade.shares,
                "requested_shares": trade.requested_shares,
                "unfilled_shares": trade.unfilled_shares,
                "pnl": trade.pnl,
                "pnl_pct": trade.pnl_pct,
                "commission": trade.commission,
                "slippage": trade.slippage,
                "spread_cost": trade.spread_cost,
                "market_impact_cost": trade.market_impact_cost,
                "timing_cost": trade.timing_cost,
                "opportunity_cost": trade.opportunity_cost,
                "participation_rate_pct": trade.participation_rate_pct,
                "implementation_shortfall": trade.implementation_shortfall,
                "borrow_cost": trade.borrow_cost,
                "locate_fee": trade.locate_fee,
                "risk_event": trade.risk_event,
            }
            for trade in trades
        ],
        "monthly_returns": run.monthly_returns,
    }
