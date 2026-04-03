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
    locate_fee: float = 0.0
    borrow_cost: float = 0.0
    status: str = "skipped"
    reason: str = ""
    risk_event: str | None = None

    @property
    def total_cost(self) -> float:
        return self.commission + self.slippage_cost + self.locate_fee + self.borrow_cost


def execute_signals(
    portfolio: Portfolio,
    signals: dict[str, float],
    current_bars: dict[str, pd.Series],
    current_prices: dict[str, float],
    max_position_pct: float,
    slippage_bps: float,
    commission_per_share: float,
    trade_date: date,
    signal_mode: str = "long_only",
    allow_short_selling: bool = False,
    max_short_position_pct: float | None = None,
    short_margin_requirement_pct: float = 50.0,
    short_locate_fee_bps: float = 0.0,
    market_impact_model: str = "constant",
    max_volume_participation: float = 0.05,
) -> list[SignalExecution]:
    """
    Execute strategy signals against the provided market bars.

    In long-only mode, negative signals reduce existing long exposure.
    In long/short mode, signals represent signed target portfolio weights.
    """
    executions: list[SignalExecution] = []
    short_limit = max_short_position_pct if max_short_position_pct is not None else max_position_pct

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

        current_price = current_prices[ticker]
        if current_price <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action="BUY" if signal > 0 else "SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="Invalid execution price",
                )
            )
            continue

        current_shares = portfolio.positions[ticker].shares if ticker in portfolio.positions else 0
        action: str
        requested_shares: int

        if signal_mode == "long_short":
            if signal < 0 and not allow_short_selling:
                executions.append(
                    SignalExecution(
                        ticker=ticker,
                        signal=signal,
                        action="SELL",
                        requested_shares=0,
                        status="skipped",
                        reason="Short selling is disabled for this run",
                    )
                )
                continue

            target_weight = signal
            if signal > 0:
                target_weight = min(signal, max_position_pct / 100)
            elif signal < 0:
                target_weight = max(signal, -(short_limit / 100))

            target_value = portfolio.total_equity * target_weight
            target_shares = int(target_value / current_price)
            share_delta = target_shares - current_shares
            if share_delta == 0:
                executions.append(
                    SignalExecution(
                        ticker=ticker,
                        signal=signal,
                        action="BUY" if signal > 0 else "SELL",
                        requested_shares=0,
                        status="skipped",
                        reason="Signal was already reflected in the current position",
                    )
                )
                continue

            action = "BUY" if share_delta > 0 else "SELL"
            requested_shares = abs(share_delta)
        else:
            if signal > 0:
                target_weight = min(signal, max_position_pct / 100)
                target_value = portfolio.total_equity * target_weight
                target_shares = int(target_value / current_price)
                share_delta = target_shares - current_shares
                if share_delta <= 0:
                    executions.append(
                        SignalExecution(
                            ticker=ticker,
                            signal=signal,
                            action="BUY",
                            requested_shares=max(share_delta, 0),
                            status="skipped",
                            reason="Signal did not increase exposure beyond the current position",
                        )
                    )
                    continue
                action = "BUY"
                requested_shares = share_delta
            else:
                if current_shares <= 0:
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
                requested_shares = current_shares
                if abs(signal) < 1:
                    requested_shares = int(current_shares * abs(signal))
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
                action = "SELL"

        bar = current_bars[ticker]
        fill = simulate_fill(
            side=action,
            shares=requested_shares,
            bar_open=float(bar["open"]),
            bar_high=float(bar["high"]),
            bar_low=float(bar["low"]),
            bar_close=float(bar["close"]),
            bar_volume=int(bar["volume"]),
            slippage_bps=slippage_bps,
            commission_per_share=commission_per_share,
            market_impact_model=market_impact_model,
            max_volume_participation=max_volume_participation,
        )
        if not fill.filled or fill.shares_filled <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action=action,
                    requested_shares=requested_shares,
                    status="rejected",
                    reason=fill.reason or "Order could not be filled",
                )
            )
            continue

        transaction = portfolio.apply_transaction(
            ticker=ticker,
            side=action,
            shares=fill.shares_filled,
            fill_price=fill.fill_price,
            commission=fill.commission,
            slippage_cost=fill.slippage_cost,
            trade_date=trade_date,
            requested_shares=fill.requested_shares,
            spread_cost=fill.spread_cost,
            market_impact_cost=fill.market_impact_cost,
            timing_cost=fill.timing_cost,
            opportunity_cost=fill.opportunity_cost,
            participation_rate_pct=fill.participation_rate_pct,
            allow_short_selling=allow_short_selling and signal_mode == "long_short",
            short_margin_requirement_pct=short_margin_requirement_pct,
            short_locate_fee_bps=short_locate_fee_bps,
        )
        if transaction.executed_shares <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=signal,
                    action=action,
                    requested_shares=requested_shares,
                    status="rejected",
                    reason="Order failed cash or margin checks",
                )
            )
            continue

        fully_executed = transaction.executed_shares == fill.requested_shares
        executions.append(
            SignalExecution(
                ticker=ticker,
                signal=signal,
                action=action,
                requested_shares=requested_shares,
                filled_shares=transaction.executed_shares,
                fill_price=fill.fill_price,
                commission=transaction.commission,
                slippage_cost=transaction.slippage,
                locate_fee=transaction.locate_fee,
                borrow_cost=transaction.borrow_cost,
                status="filled" if fully_executed else "partial",
                reason="Executed successfully"
                if fully_executed
                else "Executed partially due to volume, cash, or margin constraints",
            )
        )

    return executions


def execute_target_weights(
    portfolio: Portfolio,
    target_weights: dict[str, float],
    current_bars: dict[str, pd.Series],
    current_prices: dict[str, float],
    slippage_bps: float,
    commission_per_share: float,
    trade_date: date,
    allow_short_selling: bool = False,
    short_margin_requirement_pct: float = 50.0,
    short_locate_fee_bps: float = 0.0,
    market_impact_model: str = "constant",
    max_volume_participation: float = 0.05,
) -> list[SignalExecution]:
    """
    Rebalance the portfolio to explicit target weights.

    The caller is responsible for applying any portfolio construction logic.
    This executor focuses on turning target weights into realistic fills.
    """
    planned: list[tuple[int, str, float, str, int]] = []
    executions: list[SignalExecution] = []
    tickers = set(target_weights) | set(portfolio.positions)

    for ticker in tickers:
        if ticker not in current_bars or ticker not in current_prices:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=target_weights.get(ticker, 0.0),
                    action="BUY" if target_weights.get(ticker, 0.0) >= 0 else "SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="No market data available for execution",
                )
            )
            continue

        current_price = current_prices[ticker]
        if current_price <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=target_weights.get(ticker, 0.0),
                    action="BUY" if target_weights.get(ticker, 0.0) >= 0 else "SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="Invalid execution price",
                )
            )
            continue

        target_weight = target_weights.get(ticker, 0.0)
        if target_weight < 0 and not allow_short_selling:
            target_weight = 0.0

        current_shares = portfolio.positions[ticker].shares if ticker in portfolio.positions else 0
        target_value = portfolio.total_equity * target_weight
        target_shares = int(target_value / current_price)
        if target_shares == current_shares:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=target_weight,
                    action="BUY" if target_weight >= 0 else "SELL",
                    requested_shares=0,
                    status="skipped",
                    reason="Target already matched the current position",
                )
            )
            continue

        if current_shares > 0 and target_shares < 0:
            planned.append((0, ticker, 0.0, "SELL", current_shares))
            planned.append((1, ticker, target_weight, "SELL", abs(target_shares)))
            continue

        if current_shares < 0 and target_shares > 0:
            planned.append((0, ticker, 0.0, "BUY", abs(current_shares)))
            planned.append((1, ticker, target_weight, "BUY", target_shares))
            continue

        share_delta = target_shares - current_shares
        action = "BUY" if share_delta > 0 else "SELL"
        planned.append((2, ticker, target_weight, action, abs(share_delta)))

    planned.sort(key=lambda item: (item[0], 0 if item[3] == "SELL" else 1, -item[4]))

    for _, ticker, target_weight, action, requested_shares in planned:
        bar = current_bars[ticker]
        fill = simulate_fill(
            side=action,
            shares=requested_shares,
            bar_open=float(bar["open"]),
            bar_high=float(bar["high"]),
            bar_low=float(bar["low"]),
            bar_close=float(bar["close"]),
            bar_volume=int(bar["volume"]),
            slippage_bps=slippage_bps,
            commission_per_share=commission_per_share,
            market_impact_model=market_impact_model,
            max_volume_participation=max_volume_participation,
        )
        if not fill.filled or fill.shares_filled <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=target_weight,
                    action=action,
                    requested_shares=requested_shares,
                    status="rejected",
                    reason=fill.reason or "Order could not be filled",
                )
            )
            continue

        transaction = portfolio.apply_transaction(
            ticker=ticker,
            side=action,
            shares=fill.shares_filled,
            fill_price=fill.fill_price,
            commission=fill.commission,
            slippage_cost=fill.slippage_cost,
            trade_date=trade_date,
            requested_shares=fill.requested_shares,
            spread_cost=fill.spread_cost,
            market_impact_cost=fill.market_impact_cost,
            timing_cost=fill.timing_cost,
            opportunity_cost=fill.opportunity_cost,
            participation_rate_pct=fill.participation_rate_pct,
            allow_short_selling=allow_short_selling,
            short_margin_requirement_pct=short_margin_requirement_pct,
            short_locate_fee_bps=short_locate_fee_bps,
        )
        if transaction.executed_shares <= 0:
            executions.append(
                SignalExecution(
                    ticker=ticker,
                    signal=target_weight,
                    action=action,
                    requested_shares=requested_shares,
                    status="rejected",
                    reason="Order failed cash or margin checks",
                )
            )
            continue

        fully_executed = transaction.executed_shares == fill.requested_shares
        executions.append(
            SignalExecution(
                ticker=ticker,
                signal=target_weight,
                action=action,
                requested_shares=requested_shares,
                filled_shares=transaction.executed_shares,
                fill_price=fill.fill_price,
                commission=transaction.commission,
                slippage_cost=transaction.slippage,
                locate_fee=transaction.locate_fee,
                borrow_cost=transaction.borrow_cost,
                reason="Executed successfully"
                if fully_executed
                else "Executed partially due to volume, cash, or margin constraints",
                status="filled" if fully_executed else "partial",
            )
        )

    return executions
