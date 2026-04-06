from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, TypeVar, cast

import pandas as pd

from app.services import cache
from app.utils.datetime import utc_now_iso

T = TypeVar("T")


class ProviderError(RuntimeError):
    def __init__(self, provider: str, operation: str, message: str):
        super().__init__(f"{provider} {operation} failed: {message}")
        self.provider = provider
        self.operation = operation
        self.message = message


@dataclass(frozen=True)
class ProviderStatusSnapshot:
    domain: str
    provider: str
    status: str
    last_success_at: str | None
    last_error_at: str | None
    last_error: str | None
    cache_prefix: str


class ProviderRuntimeMixin:
    def __init__(self, *, domain: str, provider_name: str, cache_prefix: str):
        self._domain = domain
        self._provider_name = provider_name
        self._cache_prefix = cache_prefix
        self._last_success_at: str | None = None
        self._last_error_at: str | None = None
        self._last_error: str | None = None

    def status_snapshot(self) -> dict[str, str | None]:
        status = "degraded" if self._last_error_at is not None else "ok"
        return {
            "domain": self._domain,
            "provider": self._provider_name,
            "status": status,
            "last_success_at": self._last_success_at,
            "last_error_at": self._last_error_at,
            "last_error": self._last_error,
            "cache_prefix": self._cache_prefix,
        }

    def _record_success(self):
        self._last_success_at = utc_now_iso()
        self._last_error = None
        self._last_error_at = None

    def _record_error(self, message: str):
        self._last_error = message
        self._last_error_at = utc_now_iso()

    async def _cached_load(
        self,
        *,
        operation: str,
        cache_key: str,
        ttl: float,
        loader: Callable[[], Awaitable[T] | T],
    ) -> T:
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(T, cached)

        try:
            pending = loader()
            value = await pending if inspect.isawaitable(pending) else pending
        except Exception as exc:
            self._record_error(str(exc))
            raise ProviderError(self._provider_name, operation, str(exc)) from exc

        cache.put(cache_key, value, ttl=ttl)
        self._record_success()
        return cast(T, value)


class MarketDataProvider(Protocol):
    async def fetch_price_history(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame: ...

    def status_snapshot(self) -> dict[str, str | None]: ...


class EconomicDataProvider(Protocol):
    def list_catalog(self) -> list[dict[str, str]]: ...

    async def get_indicators(
        self,
        series_ids: list[str] | None,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]: ...

    def status_snapshot(self) -> dict[str, str | None]: ...


class EarningsDataProvider(Protocol):
    async def get_earnings_overview(self, ticker: str) -> dict[str, Any]: ...

    def status_snapshot(self) -> dict[str, str | None]: ...


class NewsSentimentProvider(Protocol):
    async def get_news_sentiment(
        self,
        ticker: str,
        *,
        lookback_days: int = 30,
        limit: int = 10,
    ) -> dict[str, Any]: ...

    def status_snapshot(self) -> dict[str, str | None]: ...


class AssetMetadataProvider(Protocol):
    async def get_asset_metadata(self, ticker: str) -> dict[str, Any]: ...

    def status_snapshot(self) -> dict[str, str | None]: ...
