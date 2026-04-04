from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.datetime import utc_now_naive

if TYPE_CHECKING:
    from app.models.trade import TradeRecord


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(50))
    strategy_params: Mapped[dict] = mapped_column(JSON)
    tickers: Mapped[list] = mapped_column(JSON)
    benchmark: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    initial_capital: Mapped[float] = mapped_column(Float)
    slippage_bps: Mapped[float] = mapped_column(Float)
    commission_per_share: Mapped[float] = mapped_column(Float)
    market_impact_model: Mapped[str] = mapped_column(String(24), default="almgren_chriss")
    max_volume_participation_pct: Mapped[float] = mapped_column(Float, default=5.0)
    position_sizing: Mapped[str] = mapped_column(String(20))
    portfolio_construction_model: Mapped[str] = mapped_column(String(32), default="equal_weight")
    portfolio_lookback_days: Mapped[int] = mapped_column(Integer, default=63)
    max_position_pct: Mapped[float] = mapped_column(Float)
    max_gross_exposure_pct: Mapped[float] = mapped_column(Float, default=150.0)
    turnover_limit_pct: Mapped[float] = mapped_column(Float, default=100.0)
    max_sector_exposure_pct: Mapped[float] = mapped_column(Float, default=100.0)
    allow_short_selling: Mapped[bool] = mapped_column(Boolean, default=False)
    max_short_position_pct: Mapped[float] = mapped_column(Float, default=25.0)
    short_margin_requirement_pct: Mapped[float] = mapped_column(Float, default=50.0)
    short_borrow_rate_bps: Mapped[float] = mapped_column(Float, default=200.0)
    short_locate_fee_bps: Mapped[float] = mapped_column(Float, default=10.0)
    short_squeeze_threshold_pct: Mapped[float] = mapped_column(Float, default=15.0)
    rebalance_frequency: Mapped[str] = mapped_column(String(10))

    # Stored results
    equity_curve: Mapped[list] = mapped_column(JSON)
    clean_equity_curve: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    benchmark_curve: Mapped[list] = mapped_column(JSON)
    drawdown_series: Mapped[list] = mapped_column(JSON)
    rolling_sharpe: Mapped[list] = mapped_column(JSON)
    rolling_volatility: Mapped[list] = mapped_column(JSON)
    monthly_returns: Mapped[list] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)
    benchmark_metrics: Mapped[dict] = mapped_column(JSON)

    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True, default=None)

    # Versioning / lineage
    lineage_tag: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True
    )
    version: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    trades: Mapped[list[TradeRecord]] = relationship(
        back_populates="backtest_run", cascade="all, delete-orphan"
    )
