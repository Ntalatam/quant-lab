from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BrokerOrderRecord:
    id: str
    ticker: str
    side: str
    requested_shares: int
    filled_shares: int
    status: str
    submitted_at: datetime
    updated_at: datetime
    order_type: str = "market"
    time_in_force: str = "day"
    broker_order_id: str | None = None
    client_order_id: str | None = None
    avg_fill_price: float | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerExecutionRecord:
    id: str
    ticker: str
    side: str
    shares: int
    fill_price: float
    executed_at: datetime
    status: str = "filled"
    order_id: str | None = None
    broker_execution_id: str | None = None
    commission: float = 0.0
    slippage_cost: float = 0.0
    borrow_cost: float = 0.0
    locate_fee: float = 0.0
    spread_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    participation_rate_pct: float = 0.0
    risk_event: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerSyncResult:
    orders: list[BrokerOrderRecord] = field(default_factory=list)
    executions: list[BrokerExecutionRecord] = field(default_factory=list)
    account_label: str | None = None
    open_order_count: int = 0
