from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaperTradingSession(Base):
    __tablename__ = "paper_trading_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="draft")

    strategy_id: Mapped[str] = mapped_column(String(50))
    strategy_params: Mapped[dict] = mapped_column(JSON)
    tickers: Mapped[list] = mapped_column(JSON)
    benchmark: Mapped[str] = mapped_column(String(10))

    bar_interval: Mapped[str] = mapped_column(String(10), default="1m")
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)

    initial_capital: Mapped[float] = mapped_column(Float)
    slippage_bps: Mapped[float] = mapped_column(Float)
    commission_per_share: Mapped[float] = mapped_column(Float)
    max_position_pct: Mapped[float] = mapped_column(Float)

    cash: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float, default=0.0)
    total_equity: Mapped[float] = mapped_column(Float)
    total_return_pct: Mapped[float] = mapped_column(Float, default=0.0)

    last_price_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    positions: Mapped[list["PaperTradingPosition"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    events: Mapped[list["PaperTradingEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    equity_points: Mapped[list["PaperTradingEquityPoint"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class PaperTradingPosition(Base):
    __tablename__ = "paper_trading_positions"
    __table_args__ = (UniqueConstraint("session_id", "ticker", name="uq_paper_session_ticker"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_trading_sessions.id")
    )
    ticker: Mapped[str] = mapped_column(String(10))
    shares: Mapped[int] = mapped_column(Integer)
    avg_cost: Mapped[float] = mapped_column(Float)
    entry_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    market_value: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    session: Mapped["PaperTradingSession"] = relationship(back_populates="positions")


class PaperTradingEvent(Base):
    __tablename__ = "paper_trading_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_trading_sessions.id")
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_type: Mapped[str] = mapped_column(String(20))
    ticker: Mapped[str | None] = mapped_column(String(10), nullable=True)
    action: Mapped[str] = mapped_column(String(30))
    signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text)

    session: Mapped["PaperTradingSession"] = relationship(back_populates="events")


class PaperTradingEquityPoint(Base):
    __tablename__ = "paper_trading_equity_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_trading_sessions.id")
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    equity: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float)

    session: Mapped["PaperTradingSession"] = relationship(back_populates="equity_points")
