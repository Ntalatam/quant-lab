from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PaperSessionStatus = Literal["draft", "active", "paused", "stopped", "error"]
PaperEventType = Literal["status", "signal", "fill", "error"]
BarInterval = Literal["1m", "5m", "15m", "1h", "1d"]


class PaperTradingSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=100)
    strategy_id: str
    params: dict = Field(default_factory=dict)
    tickers: list[str] = Field(min_length=1, max_length=10)
    benchmark: str = "SPY"
    initial_capital: float = Field(default=100_000, gt=0)
    slippage_bps: float = Field(default=5.0, ge=0, le=100)
    commission_per_share: float = Field(default=0.005, ge=0, le=5)
    max_position_pct: float = Field(default=25.0, gt=0, le=100)
    allow_short_selling: bool = False
    max_short_position_pct: float = Field(default=25.0, gt=0, le=100)
    short_margin_requirement_pct: float = Field(default=50.0, ge=0, le=100)
    short_borrow_rate_bps: float = Field(default=200.0, ge=0, le=10_000)
    short_locate_fee_bps: float = Field(default=10.0, ge=0, le=1_000)
    short_squeeze_threshold_pct: float = Field(default=15.0, ge=1, le=100)
    bar_interval: BarInterval = "1m"
    polling_interval_seconds: int = Field(default=60, ge=15, le=3600)
    start_immediately: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Session name must be at least 3 characters")
        return normalized

    @field_validator("strategy_id")
    @classmethod
    def normalize_strategy_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Strategy is required")
        return normalized

    @field_validator("benchmark")
    @classmethod
    def normalize_benchmark(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Benchmark is required")
        return normalized

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, values: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(ticker.strip().upper() for ticker in values if ticker.strip()))
        if not normalized:
            raise ValueError("At least one ticker is required")
        return normalized


class PaperTradingSessionSummary(BaseModel):
    id: str
    name: str
    status: PaperSessionStatus
    strategy_id: str
    tickers: list[str]
    bar_interval: BarInterval
    polling_interval_seconds: int
    initial_capital: float
    cash: float
    market_value: float
    total_equity: float
    total_return_pct: float
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    last_price_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    last_error: str | None = None


class PaperTradingPositionView(BaseModel):
    ticker: str
    shares: int
    avg_cost: float
    entry_date: datetime | None = None
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    accrued_borrow_cost: float = 0.0
    accrued_locate_fee: float = 0.0
    updated_at: datetime | None = None


class PaperTradingEventView(BaseModel):
    id: str
    timestamp: datetime
    event_type: PaperEventType
    ticker: str | None = None
    action: str
    signal: float | None = None
    shares: int | None = None
    fill_price: float | None = None
    status: str
    message: str


class PaperTradingEquityPointView(BaseModel):
    timestamp: datetime
    equity: float
    cash: float
    market_value: float


class PaperTradingSessionDetail(PaperTradingSessionSummary):
    benchmark: str
    strategy_params: dict
    slippage_bps: float
    commission_per_share: float
    max_position_pct: float
    allow_short_selling: bool
    max_short_position_pct: float
    short_margin_requirement_pct: float
    short_borrow_rate_bps: float
    short_locate_fee_bps: float
    short_squeeze_threshold_pct: float
    positions: list[PaperTradingPositionView]
    recent_events: list[PaperTradingEventView]
    equity_curve: list[PaperTradingEquityPointView]
