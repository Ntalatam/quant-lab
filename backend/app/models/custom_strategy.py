from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.datetime import utc_now_naive


class CustomStrategy(Base):
    __tablename__ = "custom_strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    requires_short_selling: Mapped[bool] = mapped_column(Boolean, default=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    param_schema: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    default_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )
