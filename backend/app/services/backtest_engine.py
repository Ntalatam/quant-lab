"""
Core backtesting engine.

Event-driven simulation loop — processes one bar at a time, maintaining
realistic portfolio state. The strategy ONLY sees data up to and including
the current bar (no lookahead bias).
"""

import uuid

import numpy as np
import pandas as pd
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.portfolio import Portfolio
from app.services.execution import simulate_fill
from app.services.analytics import (
    compute_all_metrics,
    compute_monthly_returns,
    compute_trade_statistics,
)
from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe
from app.services.strategy_registry import get_strategy_class
from app.schemas.backtest import BacktestConfig


from typing import Callable, Awaitable

ProgressCallback = Callable[[int, int, str, float], Awaitable[None]]


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
    start = date.fromisoformat(config.start_date)
    end = date.fromisoformat(config.end_date)

    # 1. Ensure data is loaded
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
    strategy_cls = get_strategy_class(config.strategy_id)
    strategy = strategy_cls(**config.params)
    portfolio = Portfolio(initial_capital=config.initial_capital)

    rebalance_dates = _get_rebalance_dates(all_dates, config.rebalance_frequency)

    # 5. Main simulation loop
    cumulative_cost = 0.0        # running total of commissions + slippage paid
    cost_by_date: dict = {}      # isoformat date → cumulative cost at that point
    total_bars = len(all_dates)
    # emit progress every ~1% of bars (min 1, max 50 to avoid spam)
    progress_every = max(1, min(50, total_bars // 100))

    for bar_num, current_date in enumerate(all_dates):
        current_dt = (
            current_date.date() if hasattr(current_date, "date") else current_date
        )

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

        # Mark-to-market
        portfolio.update_prices(current_prices, current_dt)

        # Only generate signals on rebalance dates
        if current_date not in rebalance_dates:
            continue

        if not data_window:
            continue

        # 6. Get signals from strategy
        signals = strategy.generate_signals(data_window, current_date)

        # 7. Process signals into orders and execute
        for ticker, signal in signals.items():
            if ticker not in current_bars:
                continue

            bar = current_bars[ticker]

            if signal > 0:  # BUY
                target_value = portfolio.total_equity * min(
                    signal, config.max_position_pct / 100
                )
                existing_value = 0
                if ticker in portfolio.positions:
                    existing_value = portfolio.positions[ticker].market_value
                buy_value = target_value - existing_value
                if buy_value <= 0:
                    continue

                shares = int(buy_value / current_prices[ticker])
                if shares <= 0:
                    continue

                fill = simulate_fill(
                    side="BUY",
                    shares=shares,
                    bar_open=float(bar["open"]),
                    bar_high=float(bar["high"]),
                    bar_low=float(bar["low"]),
                    bar_close=float(bar["close"]),
                    bar_volume=int(bar["volume"]),
                    slippage_bps=config.slippage_bps,
                    commission_per_share=config.commission_per_share,
                )
                if fill.filled:
                    portfolio.execute_buy(
                        ticker,
                        fill.shares_filled,
                        fill.fill_price,
                        fill.commission,
                        fill.slippage_cost,
                        current_dt,
                    )
                    cumulative_cost += fill.commission + fill.slippage_cost
                    cost_by_date[current_dt.isoformat()] = cumulative_cost

            elif signal < 0:  # SELL
                if ticker not in portfolio.positions:
                    continue
                shares = portfolio.positions[ticker].shares
                if abs(signal) < 1:
                    shares = int(shares * abs(signal))

                if shares <= 0:
                    continue

                fill = simulate_fill(
                    side="SELL",
                    shares=shares,
                    bar_open=float(bar["open"]),
                    bar_high=float(bar["high"]),
                    bar_low=float(bar["low"]),
                    bar_close=float(bar["close"]),
                    bar_volume=int(bar["volume"]),
                    slippage_bps=config.slippage_bps,
                    commission_per_share=config.commission_per_share,
                )
                if fill.filled:
                    portfolio.execute_sell(
                        ticker,
                        fill.shares_filled,
                        fill.fill_price,
                        fill.commission,
                        fill.slippage_cost,
                        current_dt,
                    )
                    cumulative_cost += fill.commission + fill.slippage_cost
                    cost_by_date[current_dt.isoformat()] = cumulative_cost

    # 8. Build equity curve + clean equity (no transaction costs)
    equity_curve = [
        {"date": pt["date"], "value": pt["equity"]}
        for pt in portfolio.equity_history
    ]

    # Build clean equity by forward-filling cumulative costs and adding them back
    clean_equity_curve = []
    running_cost = 0.0
    for pt in equity_curve:
        d = pt["date"]
        date_key = d.isoformat() if hasattr(d, "isoformat") else str(d)
        if date_key in cost_by_date:
            running_cost = cost_by_date[date_key]
        clean_equity_curve.append({"date": pt["date"], "value": round(pt["value"] + running_cost, 2)})

    # 9. Benchmark curve (normalized to same starting capital)
    if not benchmark_df.empty:
        bench_start = float(benchmark_df.iloc[0]["adj_close"])
        benchmark_curve = [
            {
                "date": (
                    idx.date().isoformat()
                    if hasattr(idx, "date")
                    else str(idx)
                ),
                "value": float(row["adj_close"])
                / bench_start
                * config.initial_capital,
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
    bench_metrics = compute_all_metrics(
        bench_series, bench_series, config.initial_capital
    )
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

    # Transaction cost stats
    total_commission = sum(t.commission for t in portfolio.trade_log if t.commission)
    total_slippage   = sum(t.slippage   for t in portfolio.trade_log if t.slippage)
    total_cost = total_commission + total_slippage
    metrics["total_commission"] = round(total_commission, 2)
    metrics["total_slippage"]   = round(total_slippage,   2)
    metrics["total_cost"]       = round(total_cost,       2)
    metrics["cost_drag_bps"]    = round(total_cost / config.initial_capital * 10_000, 1) if config.initial_capital else 0
    metrics["cost_drag_pct"]    = round(total_cost / config.initial_capital * 100,     3) if config.initial_capital else 0

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
    return _sanitize(result)


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
        {"date": idx.date().isoformat(), "value": round(float(v), 3)}
        for idx, v in sharpe.items()
    ]


def _rolling_volatility(returns: pd.Series, window: int = 63) -> list[dict]:
    vol = returns.rolling(window).std() * np.sqrt(252) * 100
    vol = vol.dropna()
    return [
        {"date": idx.date().isoformat(), "value": round(float(v), 3)}
        for idx, v in vol.items()
    ]


def _drawdown_series(equity: pd.Series) -> list[dict]:
    rolling_max = equity.expanding().max()
    drawdown = ((equity - rolling_max) / rolling_max) * 100
    return [
        {"date": idx.date().isoformat(), "value": round(float(v), 3)}
        for idx, v in drawdown.items()
    ]


def _trade_to_dict(trade) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "ticker": trade.ticker,
        "side": trade.side,
        "entry_date": trade.entry_date.isoformat() if trade.entry_date else None,
        "entry_price": trade.entry_price,
        "exit_date": trade.exit_date.isoformat() if trade.exit_date else None,
        "exit_price": trade.exit_price,
        "shares": trade.shares,
        "pnl": trade.pnl,
        "pnl_pct": trade.pnl_pct,
        "commission": trade.commission,
        "slippage": trade.slippage,
    }


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
