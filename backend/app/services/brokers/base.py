from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import PaperTradingSession
from app.services.brokers.types import BrokerOrderRecord, BrokerSyncResult

BROKER_OPEN_ORDER_STATUSES = {"new", "accepted", "pending_new", "open", "partially_filled"}
BROKER_FINAL_ORDER_STATUSES = {
    "filled",
    "partially_filled",
    "canceled",
    "cancelled",
    "rejected",
    "expired",
    "done_for_day",
}


class BrokerAdapter(Protocol):
    adapter_key: str

    def default_account_label(self) -> str | None: ...

    async def load_portfolio(
        self,
        session: PaperTradingSession,
        runtime: Any,
        db: AsyncSession,
    ) -> None: ...

    async def sync_account_state(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        current_prices: dict[str, float],
        snapshot_time: datetime,
        db: AsyncSession,
    ) -> BrokerSyncResult: ...

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
    ) -> BrokerSyncResult: ...

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
    ) -> BrokerSyncResult: ...

    async def cancel_open_orders(
        self,
        session: PaperTradingSession,
        runtime: Any,
        *,
        reason: str,
        db: AsyncSession,
    ) -> list[BrokerOrderRecord]: ...

    async def is_market_open(
        self,
        session: PaperTradingSession,
        *,
        snapshot_time: datetime,
    ) -> bool: ...
