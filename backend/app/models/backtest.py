from datetime import datetime

from sqlalchemy import String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    strategy_config_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("strategy_configs.id"), nullable=True
    )
    strategy_id: Mapped[str] = mapped_column(String(50))
    strategy_params: Mapped[dict] = mapped_column(JSON)
    tickers: Mapped[list] = mapped_column(JSON)
    benchmark: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    initial_capital: Mapped[float] = mapped_column(Float)
    slippage_bps: Mapped[float] = mapped_column(Float)
    commission_per_share: Mapped[float] = mapped_column(Float)
    position_sizing: Mapped[str] = mapped_column(String(20))
    max_position_pct: Mapped[float] = mapped_column(Float)
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

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    trades: Mapped[list["TradeRecord"]] = relationship(
        back_populates="backtest_run", cascade="all, delete-orphan"
    )
