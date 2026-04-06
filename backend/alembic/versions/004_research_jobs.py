"""Add persistent research jobs for async backtest workflows.

Revision ID: 004_research_jobs
Revises: 003_auth_workspace_ownership
Create Date: 2026-04-05
"""

import sqlalchemy as sa

from alembic import op

revision = "004_research_jobs"
down_revision = "003_auth_workspace_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("result_backtest_run_id", sa.String(length=36), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_message", sa.String(length=500), nullable=True),
        sa.Column("progress_date", sa.String(length=32), nullable=True),
        sa.Column("progress_equity", sa.Float(), nullable=True),
        sa.Column("logs", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["result_backtest_run_id"], ["backtest_runs.id"]),
    )
    op.create_index(
        "ix_research_jobs_workspace_id", "research_jobs", ["workspace_id"], unique=False
    )
    op.create_index(
        "ix_research_jobs_created_by_user_id",
        "research_jobs",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index("ix_research_jobs_kind", "research_jobs", ["kind"], unique=False)
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"], unique=False)
    op.create_index(
        "ix_research_jobs_result_backtest_run_id",
        "research_jobs",
        ["result_backtest_run_id"],
        unique=False,
    )
    op.create_index("ix_research_jobs_queued_at", "research_jobs", ["queued_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_research_jobs_queued_at", table_name="research_jobs")
    op.drop_index("ix_research_jobs_result_backtest_run_id", table_name="research_jobs")
    op.drop_index("ix_research_jobs_status", table_name="research_jobs")
    op.drop_index("ix_research_jobs_kind", table_name="research_jobs")
    op.drop_index("ix_research_jobs_created_by_user_id", table_name="research_jobs")
    op.drop_index("ix_research_jobs_workspace_id", table_name="research_jobs")
    op.drop_table("research_jobs")
