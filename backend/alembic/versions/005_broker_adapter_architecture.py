"""Add broker adapter metadata and persistent paper orders/executions.

Revision ID: 005_broker_adapter_architecture
Revises: 004_research_jobs
Create Date: 2026-04-05
"""

import sqlalchemy as sa

from alembic import op

revision = "005_broker_adapter_architecture"
down_revision = "004_research_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("paper_trading_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "execution_mode",
                sa.String(length=24),
                nullable=False,
                server_default="simulated_paper",
            )
        )
        batch_op.add_column(
            sa.Column(
                "broker_adapter",
                sa.String(length=24),
                nullable=False,
                server_default="paper",
            )
        )
        batch_op.add_column(sa.Column("broker_account_label", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "open_order_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    op.create_table(
        "paper_trading_orders",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("broker_order_id", sa.String(length=80), nullable=True),
        sa.Column("client_order_id", sa.String(length=80), nullable=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("side", sa.String(length=12), nullable=False),
        sa.Column("order_type", sa.String(length=24), nullable=False, server_default="market"),
        sa.Column("time_in_force", sa.String(length=16), nullable=False, server_default="day"),
        sa.Column("requested_shares", sa.Integer(), nullable=False),
        sa.Column("filled_shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="new"),
        sa.Column("avg_fill_price", sa.Float(), nullable=True),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["paper_trading_sessions.id"]),
    )
    op.create_index(
        "ix_paper_trading_orders_session_id",
        "paper_trading_orders",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_trading_orders_broker_order_id",
        "paper_trading_orders",
        ["broker_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_trading_orders_client_order_id",
        "paper_trading_orders",
        ["client_order_id"],
        unique=False,
    )

    op.create_table(
        "paper_trading_executions",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=80), nullable=True),
        sa.Column("broker_execution_id", sa.String(length=120), nullable=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("side", sa.String(length=12), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("fill_price", sa.Float(), nullable=False),
        sa.Column("commission", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("slippage_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("borrow_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("locate_fee", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("spread_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("market_impact_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("timing_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("opportunity_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("participation_rate_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="filled"),
        sa.Column("risk_event", sa.String(length=40), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["paper_trading_sessions.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["paper_trading_orders.id"]),
    )
    op.create_index(
        "ix_paper_trading_executions_session_id",
        "paper_trading_executions",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_trading_executions_order_id",
        "paper_trading_executions",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_trading_executions_broker_execution_id",
        "paper_trading_executions",
        ["broker_execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_trading_executions_broker_execution_id",
        table_name="paper_trading_executions",
    )
    op.drop_index("ix_paper_trading_executions_order_id", table_name="paper_trading_executions")
    op.drop_index(
        "ix_paper_trading_executions_session_id",
        table_name="paper_trading_executions",
    )
    op.drop_table("paper_trading_executions")

    op.drop_index(
        "ix_paper_trading_orders_client_order_id",
        table_name="paper_trading_orders",
    )
    op.drop_index(
        "ix_paper_trading_orders_broker_order_id",
        table_name="paper_trading_orders",
    )
    op.drop_index("ix_paper_trading_orders_session_id", table_name="paper_trading_orders")
    op.drop_table("paper_trading_orders")

    with op.batch_alter_table("paper_trading_sessions") as batch_op:
        batch_op.drop_column("open_order_count")
        batch_op.drop_column("broker_account_label")
        batch_op.drop_column("broker_adapter")
        batch_op.drop_column("execution_mode")
