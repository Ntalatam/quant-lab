"""Initial schema — all tables as of v1.0.

Revision ID: 001_initial
Revises:
Create Date: 2026-04-04
"""

import sqlalchemy as sa

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── price_data ──
    op.create_table(
        "price_data",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("adj_close", sa.Float, nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("ticker", "date", name="uq_ticker_date"),
    )
    op.create_index("ix_ticker_date", "price_data", ["ticker", "date"])

    # ── backtest_runs ──
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("strategy_id", sa.String(50), nullable=False),
        sa.Column("strategy_params", sa.JSON, nullable=False),
        sa.Column("tickers", sa.JSON, nullable=False),
        sa.Column("benchmark", sa.String(10), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=False),
        sa.Column("end_date", sa.String(10), nullable=False),
        sa.Column("initial_capital", sa.Float, nullable=False),
        sa.Column("slippage_bps", sa.Float, nullable=False),
        sa.Column("commission_per_share", sa.Float, nullable=False),
        sa.Column("market_impact_model", sa.String(24), server_default="almgren_chriss"),
        sa.Column("max_volume_participation_pct", sa.Float, server_default="5.0"),
        sa.Column("position_sizing", sa.String(20), nullable=False),
        sa.Column("portfolio_construction_model", sa.String(32), server_default="equal_weight"),
        sa.Column("portfolio_lookback_days", sa.Integer, server_default="63"),
        sa.Column("max_position_pct", sa.Float, nullable=False),
        sa.Column("max_gross_exposure_pct", sa.Float, server_default="150.0"),
        sa.Column("turnover_limit_pct", sa.Float, server_default="100.0"),
        sa.Column("max_sector_exposure_pct", sa.Float, server_default="100.0"),
        sa.Column("allow_short_selling", sa.Boolean, server_default="0"),
        sa.Column("max_short_position_pct", sa.Float, server_default="25.0"),
        sa.Column("short_margin_requirement_pct", sa.Float, server_default="50.0"),
        sa.Column("short_borrow_rate_bps", sa.Float, server_default="200.0"),
        sa.Column("short_locate_fee_bps", sa.Float, server_default="10.0"),
        sa.Column("short_squeeze_threshold_pct", sa.Float, server_default="15.0"),
        sa.Column("rebalance_frequency", sa.String(10), nullable=False),
        # Stored results
        sa.Column("equity_curve", sa.JSON, nullable=False),
        sa.Column("clean_equity_curve", sa.JSON, nullable=True),
        sa.Column("benchmark_curve", sa.JSON, nullable=False),
        sa.Column("drawdown_series", sa.JSON, nullable=False),
        sa.Column("rolling_sharpe", sa.JSON, nullable=False),
        sa.Column("rolling_volatility", sa.JSON, nullable=False),
        sa.Column("monthly_returns", sa.JSON, nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("benchmark_metrics", sa.JSON, nullable=False),
        sa.Column("notes", sa.String(2000), nullable=True),
        # Versioning / lineage
        sa.Column("lineage_tag", sa.String(100), nullable=True, index=True),
        sa.Column("version", sa.Integer, nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # ── trade_records ──
    op.create_table(
        "trade_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "backtest_run_id",
            sa.String(36),
            sa.ForeignKey("backtest_runs.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("position_direction", sa.String(10), server_default="LONG"),
        sa.Column("entry_date", sa.String(10), nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("exit_date", sa.String(10), nullable=True),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("shares", sa.Integer, nullable=False),
        sa.Column("requested_shares", sa.Integer, server_default="0"),
        sa.Column("unfilled_shares", sa.Integer, server_default="0"),
        sa.Column("pnl", sa.Float, nullable=True),
        sa.Column("pnl_pct", sa.Float, nullable=True),
        sa.Column("commission", sa.Float, nullable=False),
        sa.Column("slippage", sa.Float, nullable=False),
        sa.Column("spread_cost", sa.Float, server_default="0.0"),
        sa.Column("market_impact_cost", sa.Float, server_default="0.0"),
        sa.Column("timing_cost", sa.Float, server_default="0.0"),
        sa.Column("opportunity_cost", sa.Float, server_default="0.0"),
        sa.Column("participation_rate_pct", sa.Float, server_default="0.0"),
        sa.Column("implementation_shortfall", sa.Float, server_default="0.0"),
        sa.Column("borrow_cost", sa.Float, server_default="0.0"),
        sa.Column("locate_fee", sa.Float, server_default="0.0"),
        sa.Column("risk_event", sa.String(50), nullable=True),
    )

    # ── paper_trading_sessions ──
    op.create_table(
        "paper_trading_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("strategy_id", sa.String(50), nullable=False),
        sa.Column("strategy_params", sa.JSON, nullable=False),
        sa.Column("tickers", sa.JSON, nullable=False),
        sa.Column("benchmark", sa.String(10), nullable=False),
        sa.Column("bar_interval", sa.String(10), server_default="1m"),
        sa.Column("polling_interval_seconds", sa.Integer, server_default="60"),
        sa.Column("initial_capital", sa.Float, nullable=False),
        sa.Column("slippage_bps", sa.Float, nullable=False),
        sa.Column("commission_per_share", sa.Float, nullable=False),
        sa.Column("market_impact_model", sa.String(24), server_default="almgren_chriss"),
        sa.Column("max_volume_participation_pct", sa.Float, server_default="5.0"),
        sa.Column("portfolio_construction_model", sa.String(32), server_default="equal_weight"),
        sa.Column("portfolio_lookback_days", sa.Integer, server_default="63"),
        sa.Column("max_position_pct", sa.Float, nullable=False),
        sa.Column("max_gross_exposure_pct", sa.Float, server_default="150.0"),
        sa.Column("turnover_limit_pct", sa.Float, server_default="100.0"),
        sa.Column("max_sector_exposure_pct", sa.Float, server_default="100.0"),
        sa.Column("allow_short_selling", sa.Boolean, server_default="0"),
        sa.Column("max_short_position_pct", sa.Float, server_default="25.0"),
        sa.Column("short_margin_requirement_pct", sa.Float, server_default="50.0"),
        sa.Column("short_borrow_rate_bps", sa.Float, server_default="200.0"),
        sa.Column("short_locate_fee_bps", sa.Float, server_default="10.0"),
        sa.Column("short_squeeze_threshold_pct", sa.Float, server_default="15.0"),
        sa.Column("cash", sa.Float, nullable=False),
        sa.Column("market_value", sa.Float, server_default="0.0"),
        sa.Column("total_equity", sa.Float, nullable=False),
        sa.Column("total_return_pct", sa.Float, server_default="0.0"),
        sa.Column("last_price_at", sa.DateTime, nullable=True),
        sa.Column("last_signal_at", sa.DateTime, nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime, nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("stopped_at", sa.DateTime, nullable=True),
    )

    # ── paper_trading_positions ──
    op.create_table(
        "paper_trading_positions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("paper_trading_sessions.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("shares", sa.Integer, nullable=False),
        sa.Column("avg_cost", sa.Float, nullable=False),
        sa.Column("entry_date", sa.DateTime, nullable=False),
        sa.Column("current_price", sa.Float, server_default="0.0"),
        sa.Column("market_value", sa.Float, server_default="0.0"),
        sa.Column("unrealized_pnl", sa.Float, server_default="0.0"),
        sa.Column("unrealized_pnl_pct", sa.Float, server_default="0.0"),
        sa.Column("accrued_borrow_cost", sa.Float, server_default="0.0"),
        sa.Column("accrued_locate_fee", sa.Float, server_default="0.0"),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("session_id", "ticker", name="uq_paper_session_ticker"),
    )

    # ── paper_trading_events ──
    op.create_table(
        "paper_trading_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("paper_trading_sessions.id"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("ticker", sa.String(10), nullable=True),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("signal", sa.Float, nullable=True),
        sa.Column("shares", sa.Integer, nullable=True),
        sa.Column("fill_price", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), server_default="info"),
        sa.Column("message", sa.Text, nullable=False),
    )

    # ── paper_trading_equity_points ──
    op.create_table(
        "paper_trading_equity_points",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("paper_trading_sessions.id"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime, nullable=False, index=True),
        sa.Column("equity", sa.Float, nullable=False),
        sa.Column("cash", sa.Float, nullable=False),
        sa.Column("market_value", sa.Float, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("paper_trading_equity_points")
    op.drop_table("paper_trading_events")
    op.drop_table("paper_trading_positions")
    op.drop_table("paper_trading_sessions")
    op.drop_table("trade_records")
    op.drop_table("backtest_runs")
    op.drop_index("ix_ticker_date", table_name="price_data")
    op.drop_table("price_data")
