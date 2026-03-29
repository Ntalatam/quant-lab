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
    entry_date: Mapped[str] = mapped_column(String(10))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares: Mapped[int] = mapped_column(Integer)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission: Mapped[float] = mapped_column(Float)
    slippage: Mapped[float] = mapped_column(Float)

    backtest_run: Mapped["BacktestRun"] = relationship(back_populates="trades")
