from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.datetime import utc_now_naive

if TYPE_CHECKING:
    from app.models.backtest import BacktestRun
    from app.models.custom_strategy import CustomStrategy
    from app.models.paper import PaperTradingSession


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    memberships: Mapped[list[WorkspaceMembership]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_sessions: Mapped[list[RefreshTokenSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    backtests: Mapped[list[BacktestRun]] = relationship(
        back_populates="created_by_user",
    )
    custom_strategies: Mapped[list[CustomStrategy]] = relationship(
        back_populates="created_by_user",
    )
    paper_sessions: Mapped[list[PaperTradingSession]] = relationship(
        back_populates="created_by_user",
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False)
    personal_for_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    memberships: Mapped[list[WorkspaceMembership]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    backtests: Mapped[list[BacktestRun]] = relationship(
        back_populates="workspace",
    )
    custom_strategies: Mapped[list[CustomStrategy]] = relationship(
        back_populates="workspace",
    )
    paper_sessions: Mapped[list[PaperTradingSession]] = relationship(
        back_populates="workspace",
    )


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)

    user: Mapped[User] = relationship(back_populates="refresh_sessions")
