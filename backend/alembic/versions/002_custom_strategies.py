"""Add persisted custom strategies.

Revision ID: 002_custom_strategies
Revises: 001_initial
Create Date: 2026-04-04
"""

import sqlalchemy as sa

from alembic import op

revision = "002_custom_strategies"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_strategies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("signal_mode", sa.String(20), nullable=False),
        sa.Column("requires_short_selling", sa.Boolean(), server_default="0"),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("param_schema", sa.JSON(), nullable=False),
        sa.Column("default_params", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("custom_strategies")
