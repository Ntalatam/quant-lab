from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import httpx
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.paper import PaperTradingSession
from app.services.brokers.base import BROKER_OPEN_ORDER_STATUSES
from app.services.brokers.types import BrokerExecutionRecord, BrokerOrderRecord, BrokerSyncResult
from app.services.portfolio import Portfolio, Position
from app.services.trading import plan_target_weight_orders


class AlpacaPaperBrokerAdapter:
    adapter_key = "alpaca"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        if not settings.ALPACA_API_KEY or not settings.ALPACA_SECRET_KEY:
            raise ValueError("Alpaca credentials are not configured for broker paper sessions.")
        self._transport = transport

    def default_account_label(self) -> str:
        return "Alpaca paper"

    async def load_portfolio(
        self,
        session: PaperTradingSession,
        runtime: Any,
        db: AsyncSession,
    ) -> None:
        runtime.portfolio = Portfolio(initial_capital=session.initial_capital, cash=session.cash)
        await self.sync_account_state(
            session,
            runtime,
            current_prices={},
            snapshot_time=datetime.utcnow(),
            db=db,
        )

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
        account, positions, orders = await self._fetch_state(session)
        runtime.portfolio = self._build_portfolio(
            session,
            account=account,
            positions=positions,
            current_prices=current_prices,
            snapshot_time=snapshot_time,
            previous_portfolio=runtime.portfolio,
        )

        session_orders = [order for order in orders if self._is_session_order(session, order)]
        return BrokerSyncResult(
            orders=[self._build_order_record(order) for order in session_orders],
            executions=self._build_execution_records(session_orders),
            account_label=self._account_label(account),
            open_order_count=sum(
                1
                for order in session_orders
                if str(order.get("status", "")) in BROKER_OPEN_ORDER_STATUSES
            ),
        )

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
        if runtime.portfolio is None:
            runtime.portfolio = Portfolio(
                initial_capital=session.initial_capital, cash=session.cash
            )

        planned_orders, _skipped = plan_target_weight_orders(
            portfolio=runtime.portfolio,
            target_weights=target_weights,
            current_bars=current_bars,
            current_prices=current_prices,
            allow_short_selling=session.allow_short_selling,
        )

        submitted: list[BrokerOrderRecord] = []
        for planned in planned_orders:
            payload = {
                "symbol": planned.ticker,
                "qty": str(planned.requested_shares),
                "side": planned.action.lower(),
                "type": "market",
                "time_in_force": "day",
                "client_order_id": self._build_client_order_id(
                    session, suffix=uuid.uuid4().hex[:16]
                ),
            }
            raw_order = await self._request_json("POST", "/v2/orders", json=payload)
            submitted.append(
                self._build_order_record(raw_order, message="Submitted to Alpaca paper")
            )

        synced = await self.sync_account_state(
            session,
            runtime,
            current_prices=current_prices,
            snapshot_time=snapshot_time,
            db=db,
        )
        merged_orders = {order.broker_order_id or order.id: order for order in synced.orders}
        for order in submitted:
            merged_orders[order.broker_order_id or order.id] = order
        synced.orders = list(merged_orders.values())
        return synced

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
        del current_bars
        if runtime.portfolio is None:
            runtime.portfolio = Portfolio(
                initial_capital=session.initial_capital, cash=session.cash
            )

        for ticker in tickers:
            position = runtime.portfolio.positions.get(ticker)
            if position is None or position.shares >= 0:
                continue
            payload = {
                "symbol": ticker,
                "qty": str(abs(position.shares)),
                "side": "buy",
                "type": "market",
                "time_in_force": "day",
                "client_order_id": self._build_client_order_id(
                    session, suffix=f"cover-{uuid.uuid4().hex[:12]}"
                ),
            }
            await self._request_json("POST", "/v2/orders", json=payload)

        synced = await self.sync_account_state(
            session,
            runtime,
            current_prices=current_prices,
            snapshot_time=snapshot_time,
            db=db,
        )
        for order in synced.orders:
            if order.message is None:
                order.message = reason
        for execution in synced.executions:
            if execution.message is None:
                execution.message = reason
            execution.risk_event = "short_squeeze_cover"
        return synced

    async def cancel_open_orders(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        reason: str,
        db: AsyncSession,
    ) -> list[BrokerOrderRecord]:
        del runtime, db
        account, positions, orders = await self._fetch_state(session)
        del account, positions

        cancelled_orders: list[BrokerOrderRecord] = []
        for order in orders:
            if not self._is_session_order(session, order):
                continue
            if str(order.get("status", "")) not in BROKER_OPEN_ORDER_STATUSES:
                continue
            await self._request_json("DELETE", f"/v2/orders/{order['id']}")
            cancelled_orders.append(
                self._build_order_record(
                    order,
                    status_override="canceled",
                    message=reason,
                )
            )
        return cancelled_orders

    async def is_market_open(
        self,
        session: PaperTradingSession,
        *,
        snapshot_time: datetime,
    ) -> bool:
        del session, snapshot_time
        payload = await self._request_json("GET", "/v2/clock")
        return bool(payload.get("is_open", False))

    async def _fetch_state(
        self,
        session: PaperTradingSession,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        account = await self._request_json("GET", "/v2/account")
        positions = await self._request_json("GET", "/v2/positions")
        orders = await self._request_json(
            "GET",
            "/v2/orders",
            params={"status": "all", "limit": 100, "direction": "desc"},
        )
        return account, list(positions), list(orders)

    def _build_portfolio(
        self,
        session: PaperTradingSession,
        *,
        account: dict[str, Any],
        positions: list[dict[str, Any]],
        current_prices: dict[str, float],
        snapshot_time: datetime,
        previous_portfolio: Portfolio | None,
    ) -> Portfolio:
        portfolio = Portfolio(
            initial_capital=session.initial_capital,
            cash=float(account.get("cash") or account.get("buying_power") or session.cash),
        )
        if previous_portfolio is not None:
            portfolio.equity_history = previous_portfolio.equity_history

        price_map = dict(current_prices)
        for raw_position in positions:
            ticker = str(raw_position.get("symbol", "")).upper()
            qty = int(float(raw_position.get("qty", 0)))
            price = float(raw_position.get("current_price") or current_prices.get(ticker) or 0.0)
            price_map[ticker] = price
            portfolio.positions[ticker] = Position(
                ticker=ticker,
                shares=qty,
                avg_cost=float(raw_position.get("avg_entry_price", 0.0)),
                entry_date=snapshot_time.date(),
                current_price=price,
            )

        portfolio.update_prices(price_map, snapshot_time.date(), short_borrow_rate_bps=0.0)
        portfolio.equity_history = portfolio.equity_history[-500:]
        return portfolio

    def _build_order_record(
        self,
        raw_order: dict[str, Any],
        *,
        status_override: str | None = None,
        message: str | None = None,
    ) -> BrokerOrderRecord:
        filled_qty = int(float(raw_order.get("filled_qty") or 0))
        updated_at = self._parse_dt(raw_order.get("updated_at")) or datetime.utcnow()
        submitted_at = self._parse_dt(raw_order.get("submitted_at")) or updated_at
        broker_order_id = str(raw_order.get("id")) if raw_order.get("id") else None
        return BrokerOrderRecord(
            id=broker_order_id or str(uuid.uuid4()),
            broker_order_id=broker_order_id,
            client_order_id=raw_order.get("client_order_id"),
            ticker=str(raw_order.get("symbol", "")).upper(),
            side=str(raw_order.get("side", "")).lower(),
            requested_shares=int(float(raw_order.get("qty") or 0)),
            filled_shares=filled_qty,
            status=status_override or str(raw_order.get("status", "new")),
            submitted_at=submitted_at,
            updated_at=updated_at,
            order_type=str(raw_order.get("type", "market")),
            time_in_force=str(raw_order.get("time_in_force", "day")),
            avg_fill_price=(
                float(raw_order["filled_avg_price"])
                if raw_order.get("filled_avg_price") not in {None, ""}
                else None
            ),
            message=message,
            metadata=raw_order,
        )

    def _build_execution_records(
        self,
        orders: list[dict[str, Any]],
    ) -> list[BrokerExecutionRecord]:
        executions: list[BrokerExecutionRecord] = []
        for order in orders:
            filled_qty = int(float(order.get("filled_qty") or 0))
            fill_price = order.get("filled_avg_price")
            if filled_qty <= 0 or fill_price in {None, ""}:
                continue
            updated_at = self._parse_dt(order.get("updated_at")) or datetime.utcnow()
            broker_order_id = str(order.get("id")) if order.get("id") else None
            execution_id = (
                f"{broker_order_id or uuid.uuid4()}:{filled_qty}:{updated_at.isoformat()}"
            )
            executions.append(
                BrokerExecutionRecord(
                    id=execution_id,
                    order_id=broker_order_id,
                    broker_execution_id=execution_id,
                    ticker=str(order.get("symbol", "")).upper(),
                    side=str(order.get("side", "")).lower(),
                    shares=filled_qty,
                    fill_price=float(str(fill_price)),
                    executed_at=updated_at,
                    status=str(order.get("status", "filled")),
                    message="Filled via Alpaca paper",
                    metadata=order,
                )
            )
        return executions

    def _account_label(self, account: dict[str, Any]) -> str:
        account_number = str(account.get("account_number", "")).strip()
        if account_number:
            return f"Alpaca paper • {account_number[-4:]}"
        return self.default_account_label()

    def _is_session_order(self, session: PaperTradingSession, raw_order: dict[str, Any]) -> bool:
        client_order_id = str(raw_order.get("client_order_id") or "")
        return client_order_id.startswith(self._build_client_order_prefix(session))

    def _build_client_order_prefix(self, session: PaperTradingSession) -> str:
        return f"quantlab-{session.id[:8]}"

    def _build_client_order_id(self, session: PaperTradingSession, *, suffix: str) -> str:
        return f"{self._build_client_order_prefix(session)}-{suffix}"

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(
            base_url=settings.ALPACA_BASE_URL,
            timeout=20.0,
            transport=self._transport,
            headers={
                "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY,
            },
        ) as client:
            response = await client.request(method, path, params=params, json=json)
        if response.status_code >= 400:
            raise RuntimeError(f"Alpaca request failed ({response.status_code}): {response.text}")
        if response.status_code == 204:
            return {}
        return response.json()

    def _parse_dt(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
