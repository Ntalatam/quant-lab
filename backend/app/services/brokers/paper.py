from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import PaperTradingPosition, PaperTradingSession
from app.services.brokers.types import BrokerExecutionRecord, BrokerOrderRecord, BrokerSyncResult
from app.services.execution import simulate_fill
from app.services.portfolio import Portfolio, Position
from app.services.trading import SignalExecution, execute_target_weights


class SimulatedPaperBrokerAdapter:
    adapter_key = "paper"

    def default_account_label(self) -> str:
        return "Local simulator"

    async def load_portfolio(
        self,
        session: PaperTradingSession,
        runtime: Any,
        db: AsyncSession,
    ) -> None:
        portfolio = Portfolio(
            initial_capital=session.initial_capital,
            cash=session.cash,
        )
        positions_result = await db.execute(
            select(PaperTradingPosition).where(PaperTradingPosition.session_id == session.id)
        )
        for row in positions_result.scalars().all():
            portfolio.positions[row.ticker] = Position(
                ticker=row.ticker,
                shares=row.shares,
                avg_cost=row.avg_cost,
                entry_date=row.entry_date.date(),
                current_price=row.current_price,
                accrued_borrow_cost=row.accrued_borrow_cost,
                accrued_locate_fee=row.accrued_locate_fee,
            )
        runtime.portfolio = portfolio

    async def sync_account_state(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        current_prices: dict[str, float],
        snapshot_time: datetime,
        db: AsyncSession,
    ) -> BrokerSyncResult:
        del db
        if runtime.portfolio is None:
            runtime.portfolio = Portfolio(
                initial_capital=session.initial_capital, cash=session.cash
            )
        runtime.portfolio.update_prices(
            current_prices,
            snapshot_time.date(),
            short_borrow_rate_bps=session.short_borrow_rate_bps,
        )
        runtime.portfolio.equity_history = runtime.portfolio.equity_history[-500:]
        return BrokerSyncResult(account_label=self.default_account_label(), open_order_count=0)

    async def execute_target_weights(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        target_weights: dict[str, float],
        current_bars: dict[str, pd.Series],
        current_prices: dict[str, float],
        snapshot_time: datetime,
        db: AsyncSession,
    ) -> BrokerSyncResult:
        del db
        if runtime.portfolio is None:
            runtime.portfolio = Portfolio(
                initial_capital=session.initial_capital, cash=session.cash
            )

        executions = execute_target_weights(
            portfolio=runtime.portfolio,
            target_weights=target_weights,
            current_bars=current_bars,
            current_prices=current_prices,
            slippage_bps=session.slippage_bps,
            commission_per_share=session.commission_per_share,
            trade_date=snapshot_time.date(),
            allow_short_selling=session.allow_short_selling,
            short_margin_requirement_pct=session.short_margin_requirement_pct,
            short_locate_fee_bps=session.short_locate_fee_bps,
            market_impact_model=session.market_impact_model,
            max_volume_participation=session.max_volume_participation_pct / 100,
        )
        return self._execution_result(
            executions,
            snapshot_time=snapshot_time,
            default_account_label=self.default_account_label(),
        )

    async def force_cover_positions(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        tickers: list[str],
        current_bars: dict[str, pd.Series],
        current_prices: dict[str, float],
        snapshot_time: datetime,
        db: AsyncSession,
        reason: str,
    ) -> BrokerSyncResult:
        del current_prices, db
        if runtime.portfolio is None:
            runtime.portfolio = Portfolio(
                initial_capital=session.initial_capital, cash=session.cash
            )

        orders: list[BrokerOrderRecord] = []
        executions: list[BrokerExecutionRecord] = []
        for ticker in tickers:
            position = runtime.portfolio.positions.get(ticker)
            bar = current_bars.get(ticker)
            if position is None or position.shares >= 0 or bar is None:
                continue

            requested_shares = abs(position.shares)
            fill = simulate_fill(
                side="BUY",
                shares=requested_shares,
                bar_open=float(bar["open"]),
                bar_high=float(bar["high"]),
                bar_low=float(bar["low"]),
                bar_close=float(bar["close"]),
                bar_volume=int(bar["volume"]),
                slippage_bps=session.slippage_bps,
                commission_per_share=session.commission_per_share,
                market_impact_model=session.market_impact_model,
                max_volume_participation=session.max_volume_participation_pct / 100,
            )
            order_id = str(uuid.uuid4())
            order_status = "rejected"
            message = reason
            filled_shares = 0
            average_fill_price: float | None = None

            if fill.filled and fill.shares_filled > 0:
                transaction = runtime.portfolio.apply_transaction(
                    ticker=ticker,
                    side="BUY",
                    shares=fill.shares_filled,
                    fill_price=fill.fill_price,
                    commission=fill.commission,
                    slippage_cost=fill.slippage_cost,
                    trade_date=snapshot_time.date(),
                    requested_shares=fill.requested_shares,
                    spread_cost=fill.spread_cost,
                    market_impact_cost=fill.market_impact_cost,
                    timing_cost=fill.timing_cost,
                    opportunity_cost=fill.opportunity_cost,
                    participation_rate_pct=fill.participation_rate_pct,
                    risk_event="short_squeeze_cover",
                )
                if transaction.executed_shares > 0:
                    filled_shares = transaction.executed_shares
                    average_fill_price = fill.fill_price
                    order_status = (
                        "filled"
                        if transaction.executed_shares == fill.requested_shares
                        else "partial"
                    )
                    executions.append(
                        BrokerExecutionRecord(
                            id=str(uuid.uuid4()),
                            order_id=order_id,
                            ticker=ticker,
                            side="buy",
                            shares=transaction.executed_shares,
                            fill_price=fill.fill_price,
                            executed_at=snapshot_time,
                            commission=transaction.commission,
                            slippage_cost=transaction.slippage,
                            borrow_cost=transaction.borrow_cost,
                            locate_fee=transaction.locate_fee,
                            spread_cost=transaction.spread_cost,
                            market_impact_cost=transaction.market_impact_cost,
                            timing_cost=transaction.timing_cost,
                            opportunity_cost=transaction.opportunity_cost,
                            participation_rate_pct=transaction.participation_rate_pct,
                            status="filled",
                            risk_event="short_squeeze_cover",
                            message=reason,
                        )
                    )

            orders.append(
                BrokerOrderRecord(
                    id=order_id,
                    ticker=ticker,
                    side="buy",
                    requested_shares=requested_shares,
                    filled_shares=filled_shares,
                    status=order_status,
                    submitted_at=snapshot_time,
                    updated_at=snapshot_time,
                    avg_fill_price=average_fill_price,
                    message=message,
                )
            )

        return BrokerSyncResult(
            orders=orders,
            executions=executions,
            account_label=self.default_account_label(),
            open_order_count=0,
        )

    async def cancel_open_orders(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        reason: str,
        db: AsyncSession,
    ) -> list[BrokerOrderRecord]:
        del session, runtime, reason, db
        return []

    async def is_market_open(
        self,
        session: PaperTradingSession,
        *,
        snapshot_time: datetime,
    ) -> bool:
        del session, snapshot_time
        return True

    def _execution_result(
        self,
        executions: list[SignalExecution],
        *,
        snapshot_time: datetime,
        default_account_label: str,
    ) -> BrokerSyncResult:
        orders: list[BrokerOrderRecord] = []
        execution_rows: list[BrokerExecutionRecord] = []
        for execution in executions:
            if execution.requested_shares <= 0 and execution.filled_shares <= 0:
                continue

            order_id = str(uuid.uuid4())
            orders.append(
                BrokerOrderRecord(
                    id=order_id,
                    ticker=execution.ticker,
                    side=execution.action.lower(),
                    requested_shares=execution.requested_shares,
                    filled_shares=execution.filled_shares,
                    status=execution.status,
                    submitted_at=snapshot_time,
                    updated_at=snapshot_time,
                    avg_fill_price=execution.fill_price,
                    message=execution.reason,
                )
            )

            if execution.filled_shares <= 0 or execution.fill_price is None:
                continue
            execution_rows.append(
                BrokerExecutionRecord(
                    id=str(uuid.uuid4()),
                    order_id=order_id,
                    ticker=execution.ticker,
                    side=execution.action.lower(),
                    shares=execution.filled_shares,
                    fill_price=execution.fill_price,
                    executed_at=snapshot_time,
                    commission=execution.commission,
                    slippage_cost=execution.slippage_cost,
                    borrow_cost=execution.borrow_cost,
                    locate_fee=execution.locate_fee,
                    status="filled" if execution.status == "filled" else "partial",
                    message=execution.reason,
                )
            )

        return BrokerSyncResult(
            orders=orders,
            executions=execution_rows,
            account_label=default_account_label,
            open_order_count=0,
        )
