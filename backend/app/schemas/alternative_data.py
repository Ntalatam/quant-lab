from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class EconomicIndicatorCatalogEntry(BaseModel):
    id: str
    name: str
    category: str
    unit: str
    frequency: str
    description: str


class EconomicIndicatorPoint(BaseModel):
    date: str
    value: float


class EconomicIndicatorSeries(BaseModel):
    id: str
    name: str
    category: str
    unit: str
    frequency: str
    description: str
    latest_date: str | None = None
    latest_value: float | None = None
    change_pct: float | None = None
    change_direction: Literal["up", "down", "flat"] | None = None
    points: list[EconomicIndicatorPoint]


class EconomicIndicatorsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "series": [
                    {
                        "id": "FEDFUNDS",
                        "name": "Fed Funds Rate",
                        "category": "Rates",
                        "unit": "%",
                        "frequency": "monthly",
                        "description": "Effective federal funds rate.",
                        "latest_date": "2026-03-01",
                        "latest_value": 4.5,
                        "change_pct": -2.17,
                        "change_direction": "down",
                        "points": [
                            {"date": "2026-01-01", "value": 4.75},
                            {"date": "2026-02-01", "value": 4.5},
                        ],
                    }
                ]
            }
        }
    )

    series: list[EconomicIndicatorSeries]


class EarningsEvent(BaseModel):
    date: str
    event_type: Literal["scheduled", "reported"]
    title: str
    quarter_label: str | None = None
    eps_actual: float | None = None
    eps_estimate: float | None = None
    eps_surprise_pct: float | None = None
    revenue_estimate: float | None = None


class EarningsOverviewResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
                        "revenue_estimate": 109116811940.0,
                    },
                    {
                        "date": "2025-12-31",
                        "event_type": "reported",
                        "title": "Reported earnings",
                        "quarter_label": "Q4 2025",
                        "eps_actual": 2.84,
                        "eps_estimate": 2.6708,
                        "eps_surprise_pct": 6.33,
                        "revenue_estimate": None,
                    },
                ],
            }
        }
    )

    ticker: str
    next_earnings_date: str | None = None
    events: list[EarningsEvent]


class SentimentPoint(BaseModel):
    date: str
    average_score: float
    article_count: int


class SentimentArticle(BaseModel):
    id: str
    published_at: str
    publisher: str
    title: str
    summary: str
    url: str | None = None
    content_type: str | None = None
    sentiment_score: float
    sentiment_label: Literal["bullish", "neutral", "bearish"]


class NewsSentimentResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "lookback_days": 30,
                "article_count": 12,
                "average_score": 0.24,
                "signal": "bullish",
                "bullish_articles": 7,
                "neutral_articles": 3,
                "bearish_articles": 2,
                "rolling_series": [
                    {"date": "2026-03-28", "average_score": 0.1, "article_count": 2},
                    {"date": "2026-03-29", "average_score": 0.32, "article_count": 3},
                ],
                "articles": [
                    {
                        "id": "story-1",
                        "published_at": "2026-03-29T13:30:00Z",
                        "publisher": "Yahoo Finance",
                        "title": "Apple beats revenue expectations on services strength",
                        "summary": "Apple topped consensus estimates as services and iPhone demand remained resilient.",
                        "url": "https://finance.yahoo.com/example",
                        "content_type": "STORY",
                        "sentiment_score": 0.64,
                        "sentiment_label": "bullish",
                    }
                ],
            }
        }
    )

    ticker: str
    lookback_days: int
    article_count: int
    average_score: float
    signal: Literal["bullish", "neutral", "bearish"]
    bullish_articles: int
    neutral_articles: int
    bearish_articles: int
    rolling_series: list[SentimentPoint]
    articles: list[SentimentArticle]
