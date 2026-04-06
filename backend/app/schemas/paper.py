from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PaperSessionStatus = Literal["draft", "active", "paused", "stopped", "error"]
PaperEventType = Literal["status", "signal", "fill", "error"]
BarInterval = Literal["1m", "5m", "15m", "1h", "1d"]
PaperExecutionMode = Literal["simulated_paper", "broker_paper", "broker_live"]
PaperBrokerAdapter = Literal["paper", "alpaca"]


class PaperTradingSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=100)
    execution_mode: Literal["simulated_paper", "broker_paper"] = "simulated_paper"
    broker_adapter: PaperBrokerAdapter = "paper"
    strategy_id: str
    params: dict = Field(default_factory=dict)
    tickers: list[str] = Field(min_length=1, max_length=10)
    benchmark: str = "SPY"
    initial_capital: float = Field(default=100_000, gt=0)
    slippage_bps: float = Field(default=5.0, ge=0, le=100)
    commission_per_share: float = Field(default=0.005, ge=0, le=5)
    market_impact_model: str = Field(default="almgren_chriss")
    max_volume_participation_pct: float = Field(default=5.0, gt=0, le=100)
    portfolio_construction_model: str = Field(default="equal_weight")
    portfolio_lookback_days: int = Field(default=63, ge=20, le=252)
    max_position_pct: float = Field(default=25.0, gt=0, le=100)
    max_gross_exposure_pct: float = Field(default=150.0, gt=0, le=300)
    turnover_limit_pct: float = Field(default=100.0, ge=0, le=300)
    max_sector_exposure_pct: float = Field(default=100.0, gt=0, le=300)
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
        normalized = list(
            dict.fromkeys(ticker.strip().upper() for ticker in values if ticker.strip())
        )
        if not normalized:
            raise ValueError("At least one ticker is required")
        return normalized

    @field_validator("broker_adapter")
    @classmethod
    def normalize_broker_adapter(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_execution_mode(self):
        if self.execution_mode == "simulated_paper":
            self.broker_adapter = "paper"
            return self

        if self.execution_mode == "broker_paper" and self.broker_adapter == "paper":
            raise ValueError("Broker paper mode requires an external broker adapter.")
        return self


class PaperTradingSessionSummary(BaseModel):
    id: str
    name: str
    status: PaperSessionStatus
    execution_mode: PaperExecutionMode
    broker_adapter: PaperBrokerAdapter
    broker_account_label: str | None = None
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
    open_order_count: int = 0


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


class PaperTradingOrderView(BaseModel):
    id: str
    broker_order_id: str | None = None
    client_order_id: str | None = None
    submitted_at: datetime
    updated_at: datetime
    ticker: str
    side: str
    order_type: str
    time_in_force: str
    requested_shares: int
    filled_shares: int
    status: str
    avg_fill_price: float | None = None
    message: str | None = None


class PaperTradingExecutionView(BaseModel):
    id: str
    order_id: str | None = None
    broker_execution_id: str | None = None
    executed_at: datetime
    ticker: str
    side: str
    shares: int
    fill_price: float
    commission: float
    slippage_cost: float
    borrow_cost: float
    locate_fee: float
    spread_cost: float
    market_impact_cost: float
    timing_cost: float
    opportunity_cost: float
    participation_rate_pct: float
    status: str
    risk_event: str | None = None
    message: str | None = None


class PaperTradingSessionDetail(PaperTradingSessionSummary):
    benchmark: str
    strategy_params: dict
    slippage_bps: float
    commission_per_share: float
    market_impact_model: str
    max_volume_participation_pct: float
    portfolio_construction_model: str
    portfolio_lookback_days: int
    max_position_pct: float
    max_gross_exposure_pct: float
    turnover_limit_pct: float
    max_sector_exposure_pct: float
    allow_short_selling: bool
    max_short_position_pct: float
    short_margin_requirement_pct: float
    short_borrow_rate_bps: float
    short_locate_fee_bps: float
    short_squeeze_threshold_pct: float
    positions: list[PaperTradingPositionView]
    recent_events: list[PaperTradingEventView]
    recent_orders: list[PaperTradingOrderView] = Field(default_factory=list)
    recent_executions: list[PaperTradingExecutionView] = Field(default_factory=list)
    equity_curve: list[PaperTradingEquityPointView]
