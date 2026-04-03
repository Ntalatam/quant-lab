from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TradeRecord(Base):
    __tablename__ = "trade_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    backtest_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("backtest_runs.id")
    )
    ticker: Mapped[str] = mapped_column(String(10))
    side: Mapped[str] = mapped_column(String(4))
    position_direction: Mapped[str] = mapped_column(String(10), default="LONG")
    entry_date: Mapped[str] = mapped_column(String(10))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares: Mapped[int] = mapped_column(Integer)
    requested_shares: Mapped[int] = mapped_column(Integer, default=0)
    unfilled_shares: Mapped[int] = mapped_column(Integer, default=0)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission: Mapped[float] = mapped_column(Float)
    slippage: Mapped[float] = mapped_column(Float)
    spread_cost: Mapped[float] = mapped_column(Float, default=0.0)
    market_impact_cost: Mapped[float] = mapped_column(Float, default=0.0)
    timing_cost: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_cost: Mapped[float] = mapped_column(Float, default=0.0)
    participation_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    implementation_shortfall: Mapped[float] = mapped_column(Float, default=0.0)
    borrow_cost: Mapped[float] = mapped_column(Float, default=0.0)
    locate_fee: Mapped[float] = mapped_column(Float, default=0.0)
    risk_event: Mapped[str | None] = mapped_column(String(50), nullable=True)

    backtest_run: Mapped["BacktestRun"] = relationship(back_populates="trades")
