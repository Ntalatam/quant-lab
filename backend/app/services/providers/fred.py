from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import httpx

from app.config import settings
from app.services.providers.base import EconomicDataProvider, ProviderRuntimeMixin
from app.services.providers.helpers import (
    DEFAULT_ECONOMIC_INDICATORS,
    FRED_SERIES_CATALOG,
    EconomicIndicatorMeta,
    list_economic_indicator_catalog_entries,
    parse_fred_api_payload,
    parse_fred_csv_payload,
    summarize_indicator_points,
)


class FredEconomicDataProvider(ProviderRuntimeMixin, EconomicDataProvider):
    def __init__(self):
        super().__init__(domain="economic_data", provider_name="fred", cache_prefix="provider:fred")

    def list_catalog(self) -> list[dict[str, str]]:
        return list_economic_indicator_catalog_entries()

    async def get_indicators(
        self,
        series_ids: list[str] | None,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        selected = [series_id.upper() for series_id in (series_ids or DEFAULT_ECONOMIC_INDICATORS)]
        tasks = [
            self._get_indicator_series(
                series_id=series_id,
                start_date=start_date,
                end_date=end_date,
            )
            for series_id in selected
        ]
        return await asyncio.gather(*tasks)

    async def _get_indicator_series(
        self,
        *,
        series_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        cache_key = (
            f"{self._cache_prefix}:{series_id}:{start_date.isoformat()}:{end_date.isoformat()}"
        )
        return await self._cached_load(
            operation="get_indicator_series",
            cache_key=cache_key,
            ttl=60 * 60 * 12,
            loader=lambda: self._load_indicator_series(
                series_id=series_id,
                start_date=start_date,
                end_date=end_date,
            ),
        )

    async def _load_indicator_series(
        self,
        *,
        series_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        meta = FRED_SERIES_CATALOG.get(
            series_id,
            EconomicIndicatorMeta(
                id=series_id,
                name=series_id,
                category="Other",
                unit="value",
                frequency="mixed",
                description="Custom FRED series.",
            ),
        )
        points = await self._request_fred_points(
            series_id=series_id,
            start_date=start_date,
            end_date=end_date,
        )
        latest_date, latest_value, change_pct, change_direction = summarize_indicator_points(points)
        return {
            "id": meta.id,
            "name": meta.name,
            "category": meta.category,
            "unit": meta.unit,
            "frequency": meta.frequency,
            "description": meta.description,
            "latest_date": latest_date,
            "latest_value": latest_value,
            "change_pct": change_pct,
            "change_direction": change_direction,
            "points": points,
        }

    async def _request_fred_points(
        self,
        *,
        series_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if settings.FRED_API_KEY:
                response = await client.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": settings.FRED_API_KEY,
                        "file_type": "json",
                        "observation_start": start_date.isoformat(),
                        "observation_end": end_date.isoformat(),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return parse_fred_api_payload(payload.get("observations", []))

            response = await client.get(
                "https://fred.stlouisfed.org/graph/fredgraph.csv",
                params={
                    "id": series_id,
                    "cosd": start_date.isoformat(),
                    "coed": end_date.isoformat(),
                },
            )
            response.raise_for_status()
            return parse_fred_csv_payload(response.text)
