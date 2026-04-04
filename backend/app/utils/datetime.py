from __future__ import annotations

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Return the current UTC timestamp as a naive datetime.

    The project stores UTC values in SQL ``DateTime`` columns without timezone
    metadata, so callers should be explicit about that representation instead of
    using the deprecated ``datetime.utcnow()`` constructor.
    """

    return datetime.now(UTC).replace(tzinfo=None)


def utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""

    return datetime.now(UTC).isoformat()
