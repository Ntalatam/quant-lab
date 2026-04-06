from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import TradeRecord
from app.schemas.analytics import CapacityResponse, TransactionCostAnalysisResponse
from app.services.analytics_backtests import load_backtest_run_or_404, load_backtest_trades
from app.services.analytics_market_data import backtest_date_window, load_optional_price_frame


def _fill_rate(trade: TradeRecord) -> float:
    requested = trade.requested_shares or trade.shares
    return (trade.shares / max(requested, 1)) * 100


async def build_capacity_analysis(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
) -> CapacityResponse:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    trades = await load_backtest_trades(
        db,
        backtest_id,
        workspace_id=workspace_id,
    )

    if not trades:
        return CapacityResponse.model_validate(
            {
                "message": "No trades in this backtest",
                "capacity_estimates": [],
                "trade_adv_stats": [],
            }
        )

    start_date, end_date = backtest_date_window(run)
    price_cache: dict[str, pd.DataFrame] = {}
    adv_by_ticker: dict[str, float] = {}

    for ticker in {trade.ticker for trade in trades}:
        frame = await load_optional_price_frame(
            db,
            ticker,
            start_date,
            end_date,
            required_columns=("adj_close", "volume"),
        )
        if frame.empty:
            continue

        price_cache[ticker] = frame
        adv_by_ticker[ticker] = float((frame["adj_close"] * frame["volume"]).mean())

    trade_stats: list[dict[str, Any]] = []
    for trade in trades:
        if trade.ticker not in price_cache:
            continue

        price = float(trade.entry_price or 0)
        notional = float(trade.shares) * price
        adv = adv_by_ticker.get(trade.ticker, 0.0)
        if adv <= 0 or notional <= 0:
            continue

        trade_stats.append(
            {
                "ticker": trade.ticker,
                "side": trade.side,
                "date": trade.entry_date,
                "shares": trade.shares,
                "notional": round(notional, 0),
                "adv": round(adv, 0),
                "adv_participation_pct": round(notional / adv * 100, 4),
            }
        )

    if not trade_stats:
        return CapacityResponse.model_validate(
            {
                "message": "Could not compute ADV stats",
                "capacity_estimates": [],
                "trade_adv_stats": [],
            }
        )

    trade_stats.sort(key=lambda item: float(item["adv_participation_pct"]), reverse=True)
    participations = [float(item["adv_participation_pct"]) for item in trade_stats]
    max_participation = max(participations, default=0.0)
    avg_participation = float(np.mean(participations))
    p90_participation = float(np.percentile(participations, 90))

    thresholds = [1.0, 5.0, 10.0]
    capacity_estimates = []
    for threshold in thresholds:
        capacity_aum = (
            threshold / max_participation * run.initial_capital if max_participation > 0 else None
        )
        capacity_estimates.append(
            {
                "adv_threshold_pct": threshold,
                "capacity_aum": round(capacity_aum) if capacity_aum else None,
                "label": f"Max trade uses <={threshold}% of ADV",
            }
        )

    return CapacityResponse.model_validate(
        {
            "initial_capital": run.initial_capital,
            "n_trades": len(trade_stats),
            "max_adv_participation_pct": round(max_participation, 4),
            "avg_adv_participation_pct": round(avg_participation, 4),
            "p90_adv_participation_pct": round(p90_participation, 4),
            "capacity_estimates": capacity_estimates,
            "trade_adv_stats": trade_stats[:20],
        }
    )


async def build_transaction_cost_analysis(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
) -> TransactionCostAnalysisResponse:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    trades = await load_backtest_trades(
        db,
        backtest_id,
        workspace_id=workspace_id,
    )

    model = {
        "market_impact_model": run.market_impact_model or "almgren_chriss",
        "max_volume_participation_pct": run.max_volume_participation_pct or 5,
        "slippage_bps": run.slippage_bps,
        "commission_per_share": run.commission_per_share,
    }
    if not trades:
        return TransactionCostAnalysisResponse.model_validate(
            {
                "message": "No trades in this backtest",
                "model": model,
                "summary": {
                    "total_trades": 0,
                    "total_commission": 0.0,
                    "total_spread_cost": 0.0,
                    "total_market_impact_cost": 0.0,
                    "total_timing_cost": 0.0,
                    "total_opportunity_cost": 0.0,
                    "total_borrow_cost": 0.0,
                    "total_locate_fees": 0.0,
                    "total_implementation_shortfall": 0.0,
                    "avg_fill_rate_pct": 0.0,
                    "avg_participation_rate_pct": 0.0,
                    "p90_participation_rate_pct": 0.0,
                    "cost_as_pct_of_initial_capital": 0.0,
                },
                "ticker_breakdown": [],
                "top_cost_trades": [],
            }
        )

    summary = {
        "total_trades": len(trades),
        "total_commission": round(sum(trade.commission for trade in trades), 2),
        "total_spread_cost": round(sum(trade.spread_cost for trade in trades), 2),
        "total_market_impact_cost": round(sum(trade.market_impact_cost for trade in trades), 2),
        "total_timing_cost": round(sum(trade.timing_cost for trade in trades), 2),
        "total_opportunity_cost": round(sum(trade.opportunity_cost for trade in trades), 2),
        "total_borrow_cost": round(sum(trade.borrow_cost for trade in trades), 2),
        "total_locate_fees": round(sum(trade.locate_fee for trade in trades), 2),
        "total_implementation_shortfall": round(
            sum(trade.implementation_shortfall for trade in trades),
            2,
        ),
        "avg_fill_rate_pct": round(float(np.mean([_fill_rate(trade) for trade in trades])), 2),
        "avg_participation_rate_pct": round(
            float(np.mean([trade.participation_rate_pct for trade in trades])),
            3,
        ),
        "p90_participation_rate_pct": round(
            float(np.percentile([trade.participation_rate_pct for trade in trades], 90)),
            3,
        ),
        "cost_as_pct_of_initial_capital": round(
            (
                sum(trade.implementation_shortfall for trade in trades)
                / max(run.initial_capital, 1e-8)
            )
            * 100,
            3,
        ),
    }

    ticker_map: dict[str, dict[str, Any]] = {}
    for trade in trades:
        row = ticker_map.setdefault(
            trade.ticker,
            {
                "ticker": trade.ticker,
                "trades": 0,
                "total_commission": 0.0,
                "total_spread_cost": 0.0,
                "total_market_impact_cost": 0.0,
                "total_timing_cost": 0.0,
                "total_opportunity_cost": 0.0,
                "total_implementation_shortfall": 0.0,
                "fill_rates": [],
                "participation_rates": [],
            },
        )
        row["trades"] += 1
        row["total_commission"] += trade.commission
        row["total_spread_cost"] += trade.spread_cost
        row["total_market_impact_cost"] += trade.market_impact_cost
        row["total_timing_cost"] += trade.timing_cost
        row["total_opportunity_cost"] += trade.opportunity_cost
        row["total_implementation_shortfall"] += trade.implementation_shortfall
        row["fill_rates"].append(_fill_rate(trade))
        row["participation_rates"].append(trade.participation_rate_pct)

    ticker_breakdown = [
        {
            "ticker": row["ticker"],
            "trades": row["trades"],
            "total_commission": round(row["total_commission"], 2),
            "total_spread_cost": round(row["total_spread_cost"], 2),
            "total_market_impact_cost": round(row["total_market_impact_cost"], 2),
            "total_timing_cost": round(row["total_timing_cost"], 2),
            "total_opportunity_cost": round(row["total_opportunity_cost"], 2),
            "total_implementation_shortfall": round(row["total_implementation_shortfall"], 2),
            "avg_fill_rate_pct": round(float(np.mean(row["fill_rates"])), 2),
            "avg_participation_rate_pct": round(float(np.mean(row["participation_rates"])), 3),
        }
        for row in ticker_map.values()
    ]
    ticker_breakdown.sort(
        key=lambda row: row["total_implementation_shortfall"],
        reverse=True,
    )

    top_cost_trades = [
        {
            "id": trade.id,
            "ticker": trade.ticker,
            "side": trade.side,
            "position_direction": trade.position_direction,
            "date": trade.exit_date or trade.entry_date,
            "shares": trade.shares,
            "requested_shares": trade.requested_shares or trade.shares,
            "unfilled_shares": trade.unfilled_shares or 0,
            "commission": trade.commission,
            "spread_cost": trade.spread_cost,
            "market_impact_cost": trade.market_impact_cost,
            "timing_cost": trade.timing_cost,
            "opportunity_cost": trade.opportunity_cost,
            "implementation_shortfall": trade.implementation_shortfall,
            "fill_rate_pct": round(_fill_rate(trade), 2),
            "participation_rate_pct": round(trade.participation_rate_pct, 3),
            "risk_event": trade.risk_event,
        }
        for trade in sorted(
            trades,
            key=lambda item: item.implementation_shortfall,
            reverse=True,
        )[:15]
    ]

    return TransactionCostAnalysisResponse.model_validate(
        {
            "model": model,
            "summary": summary,
            "ticker_breakdown": ticker_breakdown,
            "top_cost_trades": top_cost_trades,
        }
    )
