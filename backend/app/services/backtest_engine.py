"""
Core backtesting engine.

Event-driven simulation loop — processes one bar at a time, maintaining
realistic portfolio state. The strategy ONLY sees data up to and including
the current bar (no lookahead bias).
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import date, datetime

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.observability import elapsed_ms, get_logger
from app.schemas.backtest import BacktestConfig
from app.services.analytics import (
    compute_all_metrics,
    compute_monthly_returns,
    compute_trade_statistics,
)
from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe
from app.services.execution import simulate_fill
from app.services.portfolio import Portfolio
from app.services.portfolio_optimizer import (
    PortfolioConstructionRequest,
    construct_target_weights,
)
from app.services.strategy_registry import build_strategy_instance
from app.services.trading import execute_target_weights

ProgressCallback = Callable[[int, int, str, float], Awaitable[None]]
logger = get_logger(__name__)


async def run_backtest(
    db: AsyncSession,
    config: BacktestConfig,
    on_progress: ProgressCallback | None = None,
) -> dict:
    """Execute a full backtest and return results.

    Args:
        on_progress: optional async callback(bar_num, total_bars, date_str, equity)
                     called every ~1% of bars processed.
    """
    start_time = time.perf_counter()
    log = logger.bind(
        strategy_id=config.strategy_id,
        tickers=config.tickers,
        benchmark=config.benchmark,
        rebalance_frequency=config.rebalance_frequency,
        construction_model=config.portfolio_construction_model,
    )
    log.info(
        "backtest.started",
        initial_capital=config.initial_capital,
        allow_short_selling=config.allow_short_selling,
    )
    start = date.fromisoformat(config.start_date)
    end = date.fromisoformat(config.end_date)

    # 1. Ensure data is loaded
    data_load_start = time.perf_counter()
    all_tickers = list(set(config.tickers + [config.benchmark]))
    for ticker in all_tickers:
        loaded = await ensure_data_loaded(db, ticker, start, end)
        if not loaded:
            raise ValueError(f"Could not load data for {ticker}")

    # 2. Load dataframes
    price_data = {}
    for ticker in config.tickers:
        price_data[ticker] = await get_price_dataframe(db, ticker, start, end)

    benchmark_df = await get_price_dataframe(db, config.benchmark, start, end)

    # 3. Get the union of all trading dates
    all_dates = sorted(
        set().union(
            *[set(df.index) for df in price_data.values()],
            set(benchmark_df.index),
        )
    )

    if not all_dates:
        raise ValueError("No trading dates found in the specified range")

    # 4. Initialize strategy and portfolio
    strategy = await build_strategy_instance(db, config.strategy_id, config.params)
    if strategy.requires_short_selling and not config.allow_short_selling:
        raise ValueError(f"{strategy.name} requires short selling to be enabled.")
    portfolio = Portfolio(initial_capital=config.initial_capital)

    rebalance_dates = _get_rebalance_dates(all_dates, config.rebalance_frequency)
    log.info(
        "backtest.market_data_ready",
        duration_ms=elapsed_ms(data_load_start),
        universe_size=len(config.tickers),
        total_bars=len(all_dates),
        rebalance_events=len(rebalance_dates),
    )

    # 5. Main simulation loop
    cumulative_cost = 0.0  # running total of trading + borrow costs paid
    cost_by_date: dict = {}  # isoformat date → cumulative cost at that point
    turnover_history: list[float] = []
    total_bars = len(all_dates)
    # emit progress every ~1% of bars (min 1, max 50 to avoid spam)
    progress_every = max(1, min(50, total_bars // 100))

    for bar_num, current_date in enumerate(all_dates):
        current_dt = current_date.date() if hasattr(current_date, "date") else current_date

        # Emit progress callback periodically
        if on_progress is not None and bar_num % progress_every == 0:
            current_equity = portfolio.total_equity
            await on_progress(bar_num, total_bars, current_dt.isoformat(), current_equity)

        # Build data window (only data up to current bar — no lookahead)
        data_window = {}
        current_prices = {}
        current_bars = {}

        for ticker in config.tickers:
            df = price_data[ticker]
            window = df[df.index <= current_date]
            if len(window) == 0:
                continue
            data_window[ticker] = window
            current_prices[ticker] = float(window.iloc[-1]["adj_close"])
            current_bars[ticker] = window.iloc[-1]

        forced_cover_tickers = (
            portfolio.get_short_squeeze_candidates(
                current_prices, config.short_squeeze_threshold_pct
            )
            if config.allow_short_selling
            else []
        )

        # Mark-to-market and accrue short borrow before new signals.
        portfolio.update_prices(
            current_prices,
            current_dt,
            short_borrow_rate_bps=config.short_borrow_rate_bps,
        )

        if forced_cover_tickers:
            for ticker in forced_cover_tickers:
                if ticker not in portfolio.positions or ticker not in current_bars:
                    continue
                position = portfolio.positions[ticker]
                if position.shares >= 0:
                    continue

                bar = current_bars[ticker]
                fill = simulate_fill(
                    side="BUY",
                    shares=abs(position.shares),
                    bar_open=float(bar["open"]),
                    bar_high=float(bar["high"]),
                    bar_low=float(bar["low"]),
                    bar_close=float(bar["close"]),
                    bar_volume=int(bar["volume"]),
                    slippage_bps=config.slippage_bps,
                    commission_per_share=config.commission_per_share,
                    market_impact_model=config.market_impact_model,
                    max_volume_participation=config.max_volume_participation_pct / 100,
                )
                if not fill.filled or fill.shares_filled <= 0:
                    continue

                portfolio.apply_transaction(
                    ticker=ticker,
                    side="BUY",
                    shares=fill.shares_filled,
                    fill_price=fill.fill_price,
                    commission=fill.commission,
                    slippage_cost=fill.slippage_cost,
                    trade_date=current_dt,
                    requested_shares=fill.requested_shares,
                    spread_cost=fill.spread_cost,
                    market_impact_cost=fill.market_impact_cost,
                    timing_cost=fill.timing_cost,
                    opportunity_cost=fill.opportunity_cost,
                    participation_rate_pct=fill.participation_rate_pct,
                    risk_event="short_squeeze_cover",
                )

        # Only generate signals on rebalance dates
        if current_date not in rebalance_dates:
            current_total_cost = _current_total_cost(portfolio)
            if current_total_cost != cumulative_cost:
                cumulative_cost = current_total_cost
                cost_by_date[current_dt.isoformat()] = cumulative_cost
            continue

        if not data_window:
            current_total_cost = _current_total_cost(portfolio)
            if current_total_cost != cumulative_cost:
                cumulative_cost = current_total_cost
                cost_by_date[current_dt.isoformat()] = cumulative_cost
            continue

        # 6. Get signals from strategy
        try:
            signals = strategy.generate_signals(data_window, current_date)
        except Exception:
            log.exception(
                "backtest.strategy_error",
                bar=bar_num,
                date=current_dt.isoformat(),
            )
            raise
        for ticker in forced_cover_tickers:
            if ticker in signals:
                signals[ticker] = 0.0

        construction = await construct_target_weights(
            PortfolioConstructionRequest(
                raw_signals=signals,
                data_window=data_window,
                current_prices=current_prices,
                portfolio=portfolio,
                signal_mode=strategy.signal_mode,
                construction_model=config.portfolio_construction_model,
                lookback_days=config.portfolio_lookback_days,
                max_position_pct=config.max_position_pct,
                max_short_position_pct=config.max_short_position_pct,
                max_gross_exposure_pct=config.max_gross_exposure_pct,
                turnover_limit_pct=config.turnover_limit_pct,
                max_sector_exposure_pct=config.max_sector_exposure_pct,
                allow_short_selling=config.allow_short_selling,
            )
        )
        turnover_history.append(construction.turnover_pct)

        # 7. Process target weights into orders and execute
        execute_target_weights(
            portfolio=portfolio,
            target_weights=construction.target_weights,
            current_bars=current_bars,
            current_prices=current_prices,
            slippage_bps=config.slippage_bps,
            commission_per_share=config.commission_per_share,
            trade_date=current_dt,
            allow_short_selling=config.allow_short_selling,
            short_margin_requirement_pct=config.short_margin_requirement_pct,
            short_locate_fee_bps=config.short_locate_fee_bps,
            market_impact_model=config.market_impact_model,
            max_volume_participation=config.max_volume_participation_pct / 100,
        )
        current_total_cost = _current_total_cost(portfolio)
        if current_total_cost != cumulative_cost:
            cumulative_cost = current_total_cost
            cost_by_date[current_dt.isoformat()] = cumulative_cost

    # 8. Build equity curve + clean equity (no transaction costs)
    equity_curve = [{"date": pt["date"], "value": pt["equity"]} for pt in portfolio.equity_history]

    # Build clean equity by forward-filling cumulative costs and adding them back
    clean_equity_curve = []
    running_cost = 0.0
    for pt in equity_curve:
        d = pt["date"]
        date_key = d.isoformat() if hasattr(d, "isoformat") else str(d)
        if date_key in cost_by_date:
            running_cost = cost_by_date[date_key]
        clean_equity_curve.append(
            {"date": pt["date"], "value": round(pt["value"] + running_cost, 2)}
        )

    # 9. Benchmark curve (normalized to same starting capital)
    if not benchmark_df.empty:
        bench_start = float(benchmark_df.iloc[0]["adj_close"])
        benchmark_curve = [
            {
                "date": (idx.date().isoformat() if hasattr(idx, "date") else str(idx)),
                "value": float(row["adj_close"]) / bench_start * config.initial_capital,
            }
            for idx, row in benchmark_df.iterrows()
        ]
    else:
        benchmark_curve = []

    # 10. Compute analytics
    equity_series = pd.Series(
        [pt["value"] for pt in equity_curve],
        index=pd.to_datetime([pt["date"] for pt in equity_curve]),
    )
    bench_series = pd.Series(
        [pt["value"] for pt in benchmark_curve],
        index=pd.to_datetime([pt["date"] for pt in benchmark_curve]),
    )

    metrics = compute_all_metrics(equity_series, bench_series, config.initial_capital)
    bench_metrics = compute_all_metrics(bench_series, bench_series, config.initial_capital)
    monthly = compute_monthly_returns(equity_series)

    # Trade-level stats
    trades_list = [_trade_to_dict(t) for t in portfolio.trade_log]
    trade_stats = compute_trade_statistics(trades_list)
    metrics.update(trade_stats)

    # Exposure stats
    exposures = [pt["exposure_pct"] for pt in portfolio.equity_history]
    if exposures:
        metrics["avg_exposure_pct"] = round(np.mean(exposures), 2)
        metrics["max_exposure_pct"] = round(max(exposures), 2)
    net_exposures = [pt.get("net_exposure_pct", 0.0) for pt in portfolio.equity_history]
    short_exposures = [pt.get("short_market_value", 0.0) for pt in portfolio.equity_history]
    if net_exposures:
        metrics["avg_net_exposure_pct"] = round(np.mean(net_exposures), 2)
        metrics["max_net_exposure_pct"] = round(max(abs(value) for value in net_exposures), 2)
    if short_exposures:
        short_exposure_pct = [
            (short_mv / max(abs(pt["equity"]), 1e-10)) * 100
            for pt, short_mv in zip(portfolio.equity_history, short_exposures)
        ]
        metrics["avg_short_exposure_pct"] = round(np.mean(short_exposure_pct), 2)
        metrics["max_short_exposure_pct"] = round(max(short_exposure_pct), 2)
    if turnover_history:
        metrics["avg_turnover_pct"] = round(float(np.mean(turnover_history)), 2)
        metrics["max_turnover_pct"] = round(float(max(turnover_history)), 2)

    # Transaction cost stats
    total_commission = sum(t.commission for t in portfolio.trade_log if t.commission)
    total_slippage = sum(t.slippage for t in portfolio.trade_log if t.slippage)
    total_borrow_cost = portfolio.total_borrow_cost_paid
    total_locate_fees = portfolio.total_locate_fees_paid
    total_spread_cost = sum(t.spread_cost for t in portfolio.trade_log if t.spread_cost)
    total_market_impact_cost = sum(
        t.market_impact_cost for t in portfolio.trade_log if t.market_impact_cost
    )
    total_timing_cost = sum(t.timing_cost for t in portfolio.trade_log if t.timing_cost)
    total_opportunity_cost = sum(
        t.opportunity_cost for t in portfolio.trade_log if t.opportunity_cost
    )
    total_cost = total_commission + total_slippage + total_borrow_cost + total_locate_fees
    implementation_shortfall = (
        total_commission
        + total_spread_cost
        + total_market_impact_cost
        + total_timing_cost
        + total_opportunity_cost
    )
    fill_rates = [
        (trade.shares / max(trade.requested_shares, 1)) * 100
        for trade in portfolio.trade_log
        if trade.requested_shares > 0
    ]
    participation_rates = [
        trade.participation_rate_pct
        for trade in portfolio.trade_log
        if trade.participation_rate_pct > 0
    ]
    metrics["total_commission"] = round(total_commission, 2)
    metrics["total_slippage"] = round(total_slippage, 2)
    metrics["total_borrow_cost"] = round(total_borrow_cost, 2)
    metrics["total_locate_fees"] = round(total_locate_fees, 2)
    metrics["total_spread_cost"] = round(total_spread_cost, 2)
    metrics["total_market_impact_cost"] = round(total_market_impact_cost, 2)
    metrics["total_timing_cost"] = round(total_timing_cost, 2)
    metrics["total_opportunity_cost"] = round(total_opportunity_cost, 2)
    metrics["total_implementation_shortfall"] = round(implementation_shortfall, 2)
    metrics["avg_fill_rate_pct"] = round(float(np.mean(fill_rates)), 2) if fill_rates else 100.0
    metrics["avg_participation_rate_pct"] = (
        round(float(np.mean(participation_rates)), 3) if participation_rates else 0.0
    )
    metrics["total_cost"] = round(total_cost, 2)
    metrics["cost_drag_bps"] = (
        round(total_cost / config.initial_capital * 10_000, 1) if config.initial_capital else 0
    )
    metrics["cost_drag_pct"] = (
        round(total_cost / config.initial_capital * 100, 3) if config.initial_capital else 0
    )

    # 11. Rolling metrics
    returns = equity_series.pct_change().dropna()
    rolling_sharpe = _rolling_sharpe(returns, window=63)
    rolling_vol = _rolling_volatility(returns, window=63)
    drawdown_series = _drawdown_series(equity_series)

    # 12. Assemble result
    backtest_id = str(uuid.uuid4())
    result = {
        "id": backtest_id,
        "config": config.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
        "equity_curve": equity_curve,
        "clean_equity_curve": clean_equity_curve,
        "benchmark_curve": benchmark_curve,
        "drawdown_series": drawdown_series,
        "rolling_sharpe": rolling_sharpe,
        "rolling_volatility": rolling_vol,
        "metrics": metrics,
        "benchmark_metrics": bench_metrics,
        "trades": trades_list,
        "monthly_returns": monthly,
    }
    sanitized = _sanitize(result)
    log.info(
        "backtest.completed",
        duration_ms=elapsed_ms(start_time),
        backtest_id=backtest_id,
        total_trades=len(trades_list),
        total_return_pct=metrics.get("total_return_pct"),
        sharpe_ratio=metrics.get("sharpe_ratio"),
        max_drawdown_pct=metrics.get("max_drawdown_pct"),
    )
    return sanitized


def _get_rebalance_dates(all_dates, frequency: str) -> set:
    """Return dates on which rebalancing should occur."""
    if frequency == "daily":
        return set(all_dates)

    rebalance = set()
    prev_period = None
    for d in all_dates:
        dt = d.date() if hasattr(d, "date") else d
        if frequency == "weekly":
            period = dt.isocalendar()[1]
        elif frequency == "monthly":
            period = dt.month
        else:
            period = None

        if period != prev_period:
            rebalance.add(d)
        prev_period = period

    return rebalance


def _rolling_sharpe(returns: pd.Series, window: int = 63) -> list[dict]:
    rolling_mean = returns.rolling(window).mean()
    rolling_std = returns.rolling(window).std()
    sharpe = (rolling_mean / rolling_std) * np.sqrt(252)
    sharpe = sharpe.dropna()
    return [
        {"date": idx.date().isoformat(), "value": round(float(v), 3)} for idx, v in sharpe.items()
    ]


def _rolling_volatility(returns: pd.Series, window: int = 63) -> list[dict]:
    vol = returns.rolling(window).std() * np.sqrt(252) * 100
    vol = vol.dropna()
    return [{"date": idx.date().isoformat(), "value": round(float(v), 3)} for idx, v in vol.items()]


def _drawdown_series(equity: pd.Series) -> list[dict]:
    rolling_max = equity.expanding().max()
    drawdown = ((equity - rolling_max) / rolling_max) * 100
    return [
        {"date": idx.date().isoformat(), "value": round(float(v), 3)} for idx, v in drawdown.items()
    ]


def _trade_to_dict(trade) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "ticker": trade.ticker,
        "side": trade.side,
        "position_direction": trade.position_direction,
        "entry_date": trade.entry_date.isoformat() if trade.entry_date else None,
        "entry_price": trade.entry_price,
        "exit_date": trade.exit_date.isoformat() if trade.exit_date else None,
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


def _current_total_cost(portfolio: Portfolio) -> float:
    return round(
        sum(trade.commission + trade.slippage for trade in portfolio.trade_log)
        + portfolio.total_borrow_cost_paid
        + portfolio.total_locate_fees_paid,
        6,
    )


def _sanitize(obj):
    """Recursively replace float NaN/Inf with None so PostgreSQL JSON accepts it."""
    import math

    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
