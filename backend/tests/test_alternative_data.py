from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.services import alternative_data
from app.services.providers.registry import ProviderRegistry, set_provider_registry
from tests.auth_helpers import install_auth_overrides


class _FakeConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _statement):
        return 1


class _HealthyEngine:
    def connect(self):
        return _FakeConnection()


class _FakePaperManager:
    def __init__(self, *_args, **_kwargs):
        pass

    async def resume_active_sessions(self):
        return None

    async def shutdown(self):
        return None

    def health_summary(self):
        return {
            "runtime_sessions": 0,
            "subscriber_channels": 0,
        }


async def _noop():
    return None


def _build_client(monkeypatch):
    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", _HealthyEngine())
    app = app_main.create_app()
    install_auth_overrides(app)
    return TestClient(app)


class _BaseFakeProvider:
    def __init__(self, *, domain: str, provider: str):
        self._domain = domain
        self._provider = provider

    def status_snapshot(self) -> dict[str, str | None]:
        return {
            "domain": self._domain,
            "provider": self._provider,
            "status": "ok",
            "last_success_at": "2026-04-05T12:00:00Z",
            "last_error_at": None,
            "last_error": None,
            "cache_prefix": f"provider:{self._domain}:{self._provider}",
        }


class _FakeMarketDataProvider(_BaseFakeProvider):
    def __init__(self):
        super().__init__(domain="market_data", provider="fake-market")

    async def fetch_price_history(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        return pd.DataFrame()


class _FakeEconomicDataProvider(_BaseFakeProvider):
    def __init__(self):
        super().__init__(domain="economic_data", provider="fake-fred")

    def list_catalog(self) -> list[dict[str, str]]:
        return [
            {
                "id": "FEDFUNDS",
                "name": "Fed Funds Rate",
                "category": "Rates",
                "unit": "%",
                "frequency": "monthly",
                "description": "Effective federal funds rate.",
            },
            {
                "id": "UNRATE",
                "name": "Unemployment Rate",
                "category": "Labor",
                "unit": "%",
                "frequency": "monthly",
                "description": "Civilian unemployment rate.",
            },
        ]

    async def get_indicators(self, series_ids, start_date, end_date):
        assert series_ids == ["FEDFUNDS", "UNRATE"]
        assert start_date.isoformat() == "2024-01-01"
        assert end_date.isoformat() == "2024-12-31"
        return [
            {
                "id": "FEDFUNDS",
                "name": "Fed Funds Rate",
                "category": "Rates",
                "unit": "%",
                "frequency": "monthly",
                "description": "Effective federal funds rate.",
                "latest_date": "2024-12-01",
                "latest_value": 4.5,
                "change_pct": -2.17,
                "change_direction": "down",
                "points": [{"date": "2024-12-01", "value": 4.5}],
            }
        ]


class _FakeEarningsDataProvider(_BaseFakeProvider):
    def __init__(self):
        super().__init__(domain="earnings", provider="fake-yahoo")

    async def get_earnings_overview(self, ticker: str):
        assert ticker == "AAPL"
        return {
            "ticker": "AAPL",
            "next_earnings_date": "2026-04-30",
            "events": [
                {
                    "date": "2026-04-30",
                    "event_type": "scheduled",
                    "title": "Next earnings call",
                    "quarter_label": None,
                    "eps_actual": None,
                    "eps_estimate": 1.95,
                    "eps_surprise_pct": None,
                    "revenue_estimate": 109000000000.0,
                }
            ],
        }


class _FakeNewsSentimentProvider(_BaseFakeProvider):
    def __init__(self):
        super().__init__(domain="news_sentiment", provider="fake-yahoo")

    async def get_news_sentiment(self, ticker: str, *, lookback_days: int = 30, limit: int = 10):
        assert ticker == "AAPL"
        assert lookback_days == 30
        assert limit == 5
        return {
            "ticker": "AAPL",
            "lookback_days": 30,
            "article_count": 1,
            "average_score": 0.42,
            "signal": "bullish",
            "bullish_articles": 1,
            "neutral_articles": 0,
            "bearish_articles": 0,
            "rolling_series": [{"date": "2026-04-01", "average_score": 0.42, "article_count": 1}],
            "articles": [
                {
                    "id": "story-1",
                    "published_at": "2026-04-01T12:00:00Z",
                    "publisher": "Yahoo Finance",
                    "title": "Apple beats estimates",
                    "summary": "Services growth remains strong.",
                    "url": "https://finance.yahoo.com/example",
                    "content_type": "STORY",
                    "sentiment_score": 0.42,
                    "sentiment_label": "bullish",
                }
            ],
        }


class _FakeAssetMetadataProvider(_BaseFakeProvider):
    def __init__(self):
        super().__init__(domain="asset_metadata", provider="fake-yahoo")

    async def get_asset_metadata(self, ticker: str):
        return {"ticker": ticker, "currency": "USD"}


@pytest.fixture
def fake_provider_registry():
    registry = ProviderRegistry(
        market_data=_FakeMarketDataProvider(),
        economic_data=_FakeEconomicDataProvider(),
        earnings_data=_FakeEarningsDataProvider(),
        news_sentiment=_FakeNewsSentimentProvider(),
        asset_metadata=_FakeAssetMetadataProvider(),
    )
    set_provider_registry(registry)
    yield registry
    set_provider_registry(None)


def test_parse_fred_csv_payload_skips_missing_values():
    payload = """DATE,FEDFUNDS
2026-01-01,4.50
2026-02-01,.
2026-03-01,4.25
"""
    points = alternative_data._parse_fred_csv_payload(payload)

    assert points == [
        {"date": "2026-01-01", "value": 4.5},
        {"date": "2026-03-01", "value": 4.25},
    ]


def test_finance_sentiment_biases_headlines():
    positive = alternative_data._score_finance_sentiment(
        "Apple beats estimates and raises guidance on record services revenue"
    )
    negative = alternative_data._score_finance_sentiment(
        "Tesla misses expectations and cuts guidance after weak demand slump"
    )

    assert positive > 0.25
    assert negative < -0.25


def test_provider_status_aggregates_registry_snapshots(fake_provider_registry):
    payload = alternative_data.get_provider_status()

    assert [entry["domain"] for entry in payload] == [
        "market_data",
        "economic_data",
        "earnings",
        "news_sentiment",
        "asset_metadata",
    ]
    assert payload[1]["provider"] == "fake-fred"
    assert all(entry["status"] == "ok" for entry in payload)


def test_alternative_data_endpoints_are_typed(monkeypatch, fake_provider_registry):
    with _build_client(monkeypatch) as client:
        catalog = client.get("/api/data/economic-indicators/catalog")
        indicators = client.get(
            "/api/data/economic-indicators",
            params={
                "series_ids": ["FEDFUNDS", "UNRATE"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        earnings = client.get("/api/data/earnings", params={"ticker": "AAPL"})
        sentiment = client.get(
            "/api/data/news-sentiment",
            params={"ticker": "AAPL", "lookback_days": 30, "limit": 5},
        )
        provider_status = client.get("/api/data/providers/status")

    assert catalog.status_code == 200
    assert any(entry["id"] == "FEDFUNDS" for entry in catalog.json())

    assert indicators.status_code == 200
    assert indicators.json()["series"][0]["id"] == "FEDFUNDS"

    assert earnings.status_code == 200
    assert earnings.json()["next_earnings_date"] == "2026-04-30"

    assert sentiment.status_code == 200
    assert sentiment.json()["signal"] == "bullish"

    assert provider_status.status_code == 200
    assert provider_status.json()["providers"][0]["domain"] == "market_data"
    assert provider_status.json()["providers"][1]["provider"] == "fake-fred"
