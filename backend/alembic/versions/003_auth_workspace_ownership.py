"""Add auth, workspaces, and resource ownership.

Revision ID: 003_auth_workspace_ownership
Revises: 002_custom_strategies
Create Date: 2026-04-05
"""

import sqlalchemy as sa

from alembic import op

revision = "003_auth_workspace_ownership"
down_revision = "002_custom_strategies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("personal_for_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["personal_for_user_id"], ["users.id"]),
        sa.UniqueConstraint("personal_for_user_id", name="uq_workspaces_personal_for_user_id"),
    )

    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )

    op.create_table(
        "refresh_token_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_sessions_token_hash"),
    )
    op.create_index(
        "ix_refresh_token_sessions_user_id",
        "refresh_token_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_token_sessions_token_hash",
        "refresh_token_sessions",
        ["token_hash"],
        unique=True,
    )

    for table_name in ("backtest_runs", "custom_strategies", "paper_trading_sessions"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("workspace_id", sa.String(length=36), nullable=True))
            batch_op.add_column(
                sa.Column("created_by_user_id", sa.String(length=36), nullable=True)
            )
            batch_op.create_index(
                f"ix_{table_name}_workspace_id",
                ["workspace_id"],
                unique=False,
            )
            batch_op.create_index(
                f"ix_{table_name}_created_by_user_id",
                ["created_by_user_id"],
                unique=False,
            )
            batch_op.create_foreign_key(
                f"fk_{table_name}_workspace_id_workspaces",
                "workspaces",
                ["workspace_id"],
                ["id"],
            )
            batch_op.create_foreign_key(
                f"fk_{table_name}_created_by_user_id_users",
                "users",
                ["created_by_user_id"],
                ["id"],
            )


def downgrade() -> None:
    for table_name in ("paper_trading_sessions", "custom_strategies", "backtest_runs"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(
                f"fk_{table_name}_created_by_user_id_users",
                type_="foreignkey",
            )
            batch_op.drop_constraint(
                f"fk_{table_name}_workspace_id_workspaces",
                type_="foreignkey",
            )
            batch_op.drop_index(f"ix_{table_name}_created_by_user_id")
            batch_op.drop_index(f"ix_{table_name}_workspace_id")
            batch_op.drop_column("created_by_user_id")
            batch_op.drop_column("workspace_id")

    op.drop_index("ix_refresh_token_sessions_token_hash", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_user_id", table_name="refresh_token_sessions")
    op.drop_table("refresh_token_sessions")
    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
