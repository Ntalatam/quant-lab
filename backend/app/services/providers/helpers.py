from __future__ import annotations

import csv
import html
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

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


def list_economic_indicator_catalog_entries() -> list[dict[str, str]]:
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


def normalize_price_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    normalized = df.rename(columns=rename_map)
    if "adj_close" not in normalized.columns and "close" in normalized.columns:
        normalized["adj_close"] = normalized["close"]
    normalized = normalized[["open", "high", "low", "close", "adj_close", "volume"]].dropna(
        subset=["close"]
    )
    normalized.index = pd.to_datetime(normalized.index)
    return normalized.sort_index()


def parse_fred_api_payload(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for observation in observations:
        raw_value = observation.get("value")
        if raw_value in (None, ".", ""):
            continue
        if not isinstance(raw_value, (str, int, float)):
            continue
        points.append({"date": observation["date"], "value": round(float(raw_value), 4)})
    return points


def parse_fred_csv_payload(csv_text: str) -> list[dict[str, Any]]:
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
        points.append({"date": row["DATE"], "value": round(float(raw_value), 4)})
    return points


def summarize_indicator_points(
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
    change_pct = None
    if previous_value != 0:
        change_pct = round(((latest_value - previous_value) / abs(previous_value)) * 100, 2)

    if latest_value > previous_value:
        direction = "up"
    elif latest_value < previous_value:
        direction = "down"
    else:
        direction = "flat"
    return latest_date, latest_value, change_pct, direction


def normalize_news_article(raw_article: dict[str, Any]) -> dict[str, Any] | None:
    content = raw_article.get("content") or raw_article
    title = clean_text(content.get("title"))
    if not title:
        return None

    summary = clean_text(content.get("summary") or content.get("description"))
    published_at = content.get("pubDate")
    if not published_at:
        return None

    text = " ".join(part for part in [title, summary] if part)
    score = score_finance_sentiment(text)
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


def score_finance_sentiment(text: str) -> float:
    lower = text.lower()
    score = _SENTIMENT_ANALYZER.polarity_scores(text)["compound"]
    for phrase, weight in _POSITIVE_HINTS.items():
        if phrase in lower:
            score += weight
    for phrase, weight in _NEGATIVE_HINTS.items():
        if phrase in lower:
            score += weight
    return round(max(-1.0, min(1.0, score)), 4)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    return " ".join(text.split())


def coerce_date(value: Any) -> date | None:
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


def quarter_label(event_date: date) -> str:
    quarter = ((event_date.month - 1) // 3) + 1
    return f"Q{quarter} {event_date.year}"


def safe_float(value: Any) -> float | None:
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


def safe_percent(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    return round(number * 100, 2)
