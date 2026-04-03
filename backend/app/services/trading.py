from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.services.execution import simulate_fill
from app.services.portfolio import Portfolio


@dataclass
class SignalExecution:
    ticker: str
    signal: float
    action: str
    requested_shares: int
    filled_shares: int = 0
    fill_price: float | None = None
    commission: float = 0.0
    slippage_cost: float = 0.0
    status: str = "skipped"
    reason: str = ""

    @property
    def total_cost(self) -> float:
        return self.commission + self.slippage_cost


def execute_signals(
    portfolio: Portfolio,
    signals: dict[str, float],
    current_bars: dict[str, pd.Series],
    current_prices: dict[str, float],
    max_position_pct: float,
    slippage_bps: float,
    commission_per_share: float,
    trade_date: date,
) -> list[SignalExecution]:
    """
    Execute a batch of strategy signals against the provided market bars.

    The caller controls which bar is used for execution. Backtests pass the
    current historical bar, while paper trading can pass a synthetic "market"
    bar built from the latest live price.
    """
    executions: list[SignalExecution] = []

    for ticker, signal in signals.items():
        if signal == 0:
            continue
        if ticker not in current_bars or ticker not in current_prices:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action="BUY" if signal > 0 else "SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="No market data available for execution",
                )
            )
            continue

        bar = current_bars[ticker]

        if signal > 0:
            target_weight = min(signal, max_position_pct / 100)
            target_value = portfolio.total_equity * target_weight
            existing_value = (
                portfolio.positions[ticker].market_value
                if ticker in portfolio.positions
                else 0.0
            )
            buy_value = target_value - existing_value
            requested_shares = int(buy_value / current_prices[ticker]) if buy_value > 0 else 0

            if buy_value <= 0 or requested_shares <= 0:
                executions.append(
                    SignalExecution(
                        ticker=ticker,
                        signal=signal,
                        action="BUY",
                        requested_shares=max(requested_shares, 0),
                        status="skipped",
                        reason="Signal did not increase exposure beyond the current position",
                    )
                )
                continue

            fill = simulate_fill(
                side="BUY",
                shares=requested_shares,
                bar_open=float(bar["open"]),
                bar_high=float(bar["high"]),
                bar_low=float(bar["low"]),
                bar_close=float(bar["close"]),
                bar_volume=int(bar["volume"]),
                slippage_bps=slippage_bps,
                commission_per_share=commission_per_share,
            )
            if not fill.filled or fill.shares_filled <= 0:
                executions.append(
                    SignalExecution(
                        ticker=ticker,
                        signal=signal,
                        action="BUY",
                        requested_shares=requested_shares,
                        status="rejected",
                        reason=fill.reason or "Order could not be filled",
                    )
                )
                continue

            portfolio.execute_buy(
                ticker,
                fill.shares_filled,
                fill.fill_price,
                fill.commission,
                fill.slippage_cost,
                trade_date,
            )
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action="BUY",
                    requested_shares=requested_shares,
                    filled_shares=fill.shares_filled,
                    fill_price=fill.fill_price,
                    commission=fill.commission,
                    slippage_cost=fill.slippage_cost,
                    status="filled",
                    reason="Executed successfully",
                )
            )
            continue

        if ticker not in portfolio.positions:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action="SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="No existing position to reduce",
                )
            )
            continue

        requested_shares = portfolio.positions[ticker].shares
        if abs(signal) < 1:
            requested_shares = int(requested_shares * abs(signal))

        if requested_shares <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action="SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="Requested reduction rounded to zero shares",
                )
            )
            continue

        fill = simulate_fill(
            side="SELL",
            shares=requested_shares,
            bar_open=float(bar["open"]),
            bar_high=float(bar["high"]),
            bar_low=float(bar["low"]),
            bar_close=float(bar["close"]),
            bar_volume=int(bar["volume"]),
            slippage_bps=slippage_bps,
            commission_per_share=commission_per_share,
        )
        if not fill.filled or fill.shares_filled <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action="SELL",
                    requested_shares=requested_shares,
                    status="rejected",
                    reason=fill.reason or "Order could not be filled",
                )
            )
            continue

        portfolio.execute_sell(
            ticker,
            fill.shares_filled,
            fill.fill_price,
            fill.commission,
            fill.slippage_cost,
            trade_date,
        )
        executions.append(
            SignalExecution(
                ticker=ticker,
                signal=signal,
                action="SELL",
                requested_shares=requested_shares,
                filled_shares=fill.shares_filled,
                fill_price=fill.fill_price,
                commission=fill.commission,
                slippage_cost=fill.slippage_cost,
                status="filled",
                reason="Executed successfully",
            )
        )

    return executions
