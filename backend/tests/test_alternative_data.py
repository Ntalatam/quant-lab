from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as app_main
from app.services import alternative_data
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


def test_alternative_data_endpoints_are_typed(monkeypatch):
    async def fake_get_economic_indicators(series_ids, start_date, end_date):
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

    async def fake_get_earnings_overview(ticker):
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

    async def fake_get_news_sentiment(ticker, lookback_days, limit):
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

    monkeypatch.setattr(
        "app.api.data.get_economic_indicators",
        fake_get_economic_indicators,
    )
    monkeypatch.setattr(
        "app.api.data.get_earnings_overview",
        fake_get_earnings_overview,
    )
    monkeypatch.setattr(
        "app.api.data.get_news_sentiment",
        fake_get_news_sentiment,
    )

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

    assert catalog.status_code == 200
    assert any(entry["id"] == "FEDFUNDS" for entry in catalog.json())

    assert indicators.status_code == 200
    assert indicators.json()["series"][0]["id"] == "FEDFUNDS"

    assert earnings.status_code == 200
    assert earnings.json()["next_earnings_date"] == "2026-04-30"

    assert sentiment.status_code == 200
    assert sentiment.json()["signal"] == "bullish"
