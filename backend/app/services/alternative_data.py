from __future__ import annotations

from datetime import date
from typing import Any

from app.services.providers.helpers import parse_fred_csv_payload, score_finance_sentiment
from app.services.providers.registry import get_provider_registry

_parse_fred_csv_payload = parse_fred_csv_payload
_score_finance_sentiment = score_finance_sentiment


def list_economic_indicator_catalog() -> list[dict[str, str]]:
    return get_provider_registry().economic_data.list_catalog()


async def get_economic_indicators(
    series_ids: list[str] | None,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    return await get_provider_registry().economic_data.get_indicators(
        series_ids,
        start_date,
        end_date,
    )


async def get_earnings_overview(ticker: str) -> dict[str, Any]:
    return await get_provider_registry().earnings_data.get_earnings_overview(ticker)


async def get_news_sentiment(
    ticker: str,
    *,
    lookback_days: int = 30,
    limit: int = 10,
) -> dict[str, Any]:
    return await get_provider_registry().news_sentiment.get_news_sentiment(
        ticker,
        lookback_days=lookback_days,
        limit=limit,
    )


def get_provider_status() -> list[dict[str, str | None]]:
    return get_provider_registry().status_payload()
