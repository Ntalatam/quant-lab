from __future__ import annotations

import asyncio
import csv
import html
import io
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pandas as pd
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.config import settings
from app.observability import elapsed_ms, get_logger
from app.services import cache

logger = get_logger(__name__)

DEFAULT_ECONOMIC_INDICATORS = [
    "FEDFUNDS",
    "CPIAUCSL",
    "UNRATE",
    "DGS10",
]

_TAG_RE = re.compile(r"<[^>]+>")
_SENTIMENT_ANALYZER = SentimentIntensityAnalyzer()
_POSITIVE_HINTS = {
    "beat": 0.1,
    "beats": 0.1,
    "record": 0.08,
    "upgrade": 0.12,
    "raises guidance": 0.18,
    "strong demand": 0.12,
    "buyback": 0.08,
    "margin expansion": 0.08,
    "profit jump": 0.1,
    "outperform": 0.1,
    "surge": 0.08,
}
_NEGATIVE_HINTS = {
    "miss": -0.12,
    "misses": -0.12,
    "downgrade": -0.12,
    "cuts guidance": -0.18,
    "guidance cut": -0.18,
    "lawsuit": -0.08,
    "antitrust": -0.08,
    "recall": -0.12,
    "slump": -0.12,
    "selloff": -0.1,
    "weak demand": -0.12,
    "layoffs": -0.08,
}


@dataclass(frozen=True)
class EconomicIndicatorMeta:
    id: str
    name: str
    category: str
    unit: str
    frequency: str
    description: str


FRED_SERIES_CATALOG: dict[str, EconomicIndicatorMeta] = {
    "FEDFUNDS": EconomicIndicatorMeta(
        id="FEDFUNDS",
        name="Fed Funds Rate",
        category="Rates",
        unit="%",
        frequency="monthly",
        description="Effective federal funds rate.",
    ),
    "CPIAUCSL": EconomicIndicatorMeta(
        id="CPIAUCSL",
        name="Consumer Price Index",
        category="Inflation",
        unit="index",
        frequency="monthly",
        description="Consumer Price Index for All Urban Consumers: All Items.",
    ),
    "UNRATE": EconomicIndicatorMeta(
        id="UNRATE",
        name="Unemployment Rate",
        category="Labor",
        unit="%",
        frequency="monthly",
        description="Civilian unemployment rate.",
    ),
    "DGS10": EconomicIndicatorMeta(
        id="DGS10",
        name="10Y Treasury Yield",
        category="Rates",
        unit="%",
        frequency="daily",
        description="Market yield on U.S. Treasury securities at 10-year maturity.",
    ),
    "VIXCLS": EconomicIndicatorMeta(
        id="VIXCLS",
        name="CBOE VIX",
        category="Volatility",
        unit="index",
        frequency="daily",
        description="CBOE Volatility Index close.",
    ),
}


def list_economic_indicator_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": meta.id,
            "name": meta.name,
            "category": meta.category,
            "unit": meta.unit,
            "frequency": meta.frequency,
            "description": meta.description,
        }
        for meta in FRED_SERIES_CATALOG.values()
    ]


async def get_economic_indicators(
    series_ids: list[str] | None,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    selected = [series_id.upper() for series_id in (series_ids or DEFAULT_ECONOMIC_INDICATORS)]
    tasks = [
        _fetch_indicator_series(series_id=series_id, start_date=start_date, end_date=end_date)
        for series_id in selected
    ]
    return await asyncio.gather(*tasks)


async def _fetch_indicator_series(
    *,
    series_id: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    cache_key = f"alt:fred:{series_id}:{start_date.isoformat()}:{end_date.isoformat()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

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
    start_time = time.perf_counter()
    points = await _request_fred_points(
        series_id=series_id, start_date=start_date, end_date=end_date
    )
    latest_date, latest_value, change_pct, change_direction = _summarize_indicator_points(points)

    result = {
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
    cache.put(cache_key, result, ttl=60 * 60 * 12)
    logger.info(
        "alternative_data.fred_loaded",
        series_id=series_id,
        points=len(points),
        duration_ms=elapsed_ms(start_time),
    )
    return result


async def _request_fred_points(
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
            return _parse_fred_api_payload(payload.get("observations", []))

        response = await client.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={
                "id": series_id,
                "cosd": start_date.isoformat(),
                "coed": end_date.isoformat(),
            },
        )
        response.raise_for_status()
        return _parse_fred_csv_payload(response.text)


def _parse_fred_api_payload(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for observation in observations:
        raw_value = observation.get("value")
        if raw_value in (None, ".", ""):
            continue
        if not isinstance(raw_value, (str, int, float)):
            continue
        points.append(
            {
                "date": observation["date"],
                "value": round(float(raw_value), 4),
            }
        )
    return points


def _parse_fred_csv_payload(csv_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        return []

    value_field = next(field for field in reader.fieldnames if field != "DATE")
    points: list[dict[str, Any]] = []
    for row in reader:
        raw_value = row.get(value_field)
        if raw_value in (None, ".", ""):
            continue
        if not isinstance(raw_value, (str, int, float)):
            continue
        points.append(
            {
                "date": row["DATE"],
                "value": round(float(raw_value), 4),
            }
        )
    return points


def _summarize_indicator_points(
    points: list[dict[str, Any]],
) -> tuple[str | None, float | None, float | None, str | None]:
    if not points:
        return None, None, None, None
    latest = points[-1]
    latest_date = latest["date"]
    latest_value = round(float(latest["value"]), 4)
    if len(points) < 2:
        return latest_date, latest_value, None, None

    previous_value = float(points[-2]["value"])
    if previous_value == 0:
        change_pct = None
    else:
        change_pct = round(((latest_value - previous_value) / abs(previous_value)) * 100, 2)

    if latest_value > previous_value:
        direction = "up"
    elif latest_value < previous_value:
        direction = "down"
    else:
        direction = "flat"
    return latest_date, latest_value, change_pct, direction


async def get_earnings_overview(ticker: str) -> dict[str, Any]:
    symbol = ticker.upper()
    cache_key = f"alt:earnings:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start_time = time.perf_counter()
    result = await asyncio.to_thread(_load_earnings_overview, symbol)
    cache.put(cache_key, result, ttl=60 * 60 * 6)
    logger.info(
        "alternative_data.earnings_loaded",
        ticker=symbol,
        events=len(result["events"]),
        duration_ms=elapsed_ms(start_time),
    )
    return result


def _load_earnings_overview(ticker: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    next_earnings_date: str | None = None

    stock = yf.Ticker(ticker)

    calendar = stock.calendar or {}
    next_dates = calendar.get("Earnings Date") or []
    if not isinstance(next_dates, list):
        next_dates = [next_dates]

    scheduled_date = _coerce_date(next_dates[0]) if next_dates else None
    if scheduled_date:
        next_earnings_date = scheduled_date.isoformat()
        events.append(
            {
                "date": next_earnings_date,
                "event_type": "scheduled",
                "title": "Next earnings call",
                "quarter_label": None,
                "eps_actual": None,
                "eps_estimate": _safe_float(calendar.get("Earnings Average")),
                "eps_surprise_pct": None,
                "revenue_estimate": _safe_float(calendar.get("Revenue Average")),
            }
        )

    history = stock.earnings_history
    if isinstance(history, pd.DataFrame) and not history.empty:
        for idx, row in history.sort_index(ascending=False).head(6).iterrows():
            event_date = _coerce_date(idx)
            if event_date is None:
                continue
            events.append(
                {
                    "date": event_date.isoformat(),
                    "event_type": "reported",
                    "title": "Reported earnings",
                    "quarter_label": _quarter_label(event_date),
                    "eps_actual": _safe_float(row.get("epsActual")),
                    "eps_estimate": _safe_float(row.get("epsEstimate")),
                    "eps_surprise_pct": _safe_percent(row.get("surprisePercent")),
                    "revenue_estimate": None,
                }
            )

    events.sort(key=lambda item: item["date"], reverse=True)
    return {
        "ticker": ticker,
        "next_earnings_date": next_earnings_date,
        "events": events,
    }


async def get_news_sentiment(
    ticker: str,
    *,
    lookback_days: int = 30,
    limit: int = 10,
) -> dict[str, Any]:
    symbol = ticker.upper()
    cache_key = f"alt:sentiment:{symbol}:{lookback_days}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start_time = time.perf_counter()
    result = await asyncio.to_thread(
        _load_news_sentiment,
        symbol,
        lookback_days,
        limit,
    )
    cache.put(cache_key, result, ttl=60 * 30)
    logger.info(
        "alternative_data.sentiment_loaded",
        ticker=symbol,
        articles=result["article_count"],
        duration_ms=elapsed_ms(start_time),
    )
    return result


def _load_news_sentiment(
    ticker: str,
    lookback_days: int,
    limit: int,
) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    stock = yf.Ticker(ticker)
    raw_articles = stock.get_news(count=max(limit * 3, 12))

    articles: list[dict[str, Any]] = []
    for raw_article in raw_articles:
        article = _normalize_news_article(raw_article)
        if article is None:
            continue
        published_at = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
        if published_at < cutoff:
            continue
        articles.append(article)
        if len(articles) >= limit:
            break

    if not articles:
        return {
            "ticker": ticker,
            "lookback_days": lookback_days,
            "article_count": 0,
            "average_score": 0.0,
            "signal": "neutral",
            "bullish_articles": 0,
            "neutral_articles": 0,
            "bearish_articles": 0,
            "rolling_series": [],
            "articles": [],
        }

    by_day: dict[str, list[float]] = {}
    bullish = neutral = bearish = 0
    for article in articles:
        by_day.setdefault(article["published_at"][:10], []).append(article["sentiment_score"])
        if article["sentiment_label"] == "bullish":
            bullish += 1
        elif article["sentiment_label"] == "bearish":
            bearish += 1
        else:
            neutral += 1

    average_score = round(
        sum(article["sentiment_score"] for article in articles) / len(articles),
        4,
    )
    signal = "neutral"
    if average_score >= 0.2:
        signal = "bullish"
    elif average_score <= -0.2:
        signal = "bearish"

    rolling_series = [
        {
            "date": day,
            "average_score": round(sum(scores) / len(scores), 4),
            "article_count": len(scores),
        }
        for day, scores in sorted(by_day.items())
    ]

    return {
        "ticker": ticker,
        "lookback_days": lookback_days,
        "article_count": len(articles),
        "average_score": average_score,
        "signal": signal,
        "bullish_articles": bullish,
        "neutral_articles": neutral,
        "bearish_articles": bearish,
        "rolling_series": rolling_series,
        "articles": articles,
    }


def _normalize_news_article(raw_article: dict[str, Any]) -> dict[str, Any] | None:
    content = raw_article.get("content") or raw_article
    title = _clean_text(content.get("title"))
    if not title:
        return None

    summary = _clean_text(content.get("summary") or content.get("description"))
    published_at = content.get("pubDate")
    if not published_at:
        return None

    text = " ".join(part for part in [title, summary] if part)
    score = _score_finance_sentiment(text)
    label = "neutral"
    if score >= 0.15:
        label = "bullish"
    elif score <= -0.15:
        label = "bearish"

    provider = content.get("provider") or {}
    canonical_url = content.get("canonicalUrl") or {}

    return {
        "id": raw_article.get("id") or content.get("id") or title,
        "published_at": published_at,
        "publisher": provider.get("displayName") or "Yahoo Finance",
        "title": title,
        "summary": summary,
        "url": canonical_url.get("url"),
        "content_type": content.get("contentType"),
        "sentiment_score": score,
        "sentiment_label": label,
    }


def _score_finance_sentiment(text: str) -> float:
    lower = text.lower()
    score = _SENTIMENT_ANALYZER.polarity_scores(text)["compound"]
    for phrase, weight in _POSITIVE_HINTS.items():
        if phrase in lower:
            score += weight
    for phrase, weight in _NEGATIVE_HINTS.items():
        if phrase in lower:
            score += weight
    return round(max(-1.0, min(1.0, score)), 4)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    return " ".join(text.split())


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return None


def _quarter_label(event_date: date) -> str:
    quarter = ((event_date.month - 1) // 3) + 1
    return f"Q{quarter} {event_date.year}"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _safe_percent(value: Any) -> float | None:
    number = _safe_float(value)
    if number is None:
        return None
    return round(number * 100, 2)
