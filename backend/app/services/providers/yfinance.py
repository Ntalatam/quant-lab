from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from app.services.providers.base import (
    AssetMetadataProvider,
    EarningsDataProvider,
    MarketDataProvider,
    NewsSentimentProvider,
    ProviderRuntimeMixin,
)
from app.services.providers.helpers import (
    coerce_date,
    normalize_news_article,
    normalize_price_history,
    quarter_label,
    safe_float,
    safe_percent,
)


class YahooFinanceMarketDataProvider(ProviderRuntimeMixin, MarketDataProvider):
    def __init__(self):
        super().__init__(
            domain="market_data", provider_name="yfinance", cache_prefix="provider:market"
        )

    async def fetch_price_history(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        cache_key = f"{self._cache_prefix}:{ticker}:{start_date.isoformat()}:{end_date.isoformat()}"

        async def _load():
            df = await asyncio.to_thread(
                yf.download,
                ticker,
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                auto_adjust=False,
                progress=False,
            )
            return normalize_price_history(df)

        return await self._cached_load(
            operation="fetch_price_history",
            cache_key=cache_key,
            ttl=60 * 15,
            loader=_load,
        )


class YahooFinanceEarningsProvider(ProviderRuntimeMixin, EarningsDataProvider):
    def __init__(self):
        super().__init__(
            domain="earnings", provider_name="yfinance", cache_prefix="provider:earnings"
        )

    async def get_earnings_overview(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper()
        cache_key = f"{self._cache_prefix}:{symbol}"
        return await self._cached_load(
            operation="get_earnings_overview",
            cache_key=cache_key,
            ttl=60 * 60 * 6,
            loader=lambda: asyncio.to_thread(self._load_earnings_overview, symbol),
        )

    def _load_earnings_overview(self, ticker: str) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        next_earnings_date: str | None = None

        stock = yf.Ticker(ticker)
        calendar = stock.calendar or {}
        next_dates = calendar.get("Earnings Date") or []
        if not isinstance(next_dates, list):
            next_dates = [next_dates]

        scheduled_date = coerce_date(next_dates[0]) if next_dates else None
        if scheduled_date:
            next_earnings_date = scheduled_date.isoformat()
            events.append(
                {
                    "date": next_earnings_date,
                    "event_type": "scheduled",
                    "title": "Next earnings call",
                    "quarter_label": None,
                    "eps_actual": None,
                    "eps_estimate": safe_float(calendar.get("Earnings Average")),
                    "eps_surprise_pct": None,
                    "revenue_estimate": safe_float(calendar.get("Revenue Average")),
                }
            )

        history = stock.earnings_history
        if isinstance(history, pd.DataFrame) and not history.empty:
            for idx, row in history.sort_index(ascending=False).head(6).iterrows():
                event_date = coerce_date(idx)
                if event_date is None:
                    continue
                events.append(
                    {
                        "date": event_date.isoformat(),
                        "event_type": "reported",
                        "title": "Reported earnings",
                        "quarter_label": quarter_label(event_date),
                        "eps_actual": safe_float(row.get("epsActual")),
                        "eps_estimate": safe_float(row.get("epsEstimate")),
                        "eps_surprise_pct": safe_percent(row.get("surprisePercent")),
                        "revenue_estimate": None,
                    }
                )

        events.sort(key=lambda item: item["date"], reverse=True)
        return {
            "ticker": ticker,
            "next_earnings_date": next_earnings_date,
            "events": events,
        }


class YahooFinanceNewsSentimentProvider(ProviderRuntimeMixin, NewsSentimentProvider):
    def __init__(self):
        super().__init__(
            domain="news_sentiment",
            provider_name="yfinance",
            cache_prefix="provider:news",
        )

    async def get_news_sentiment(
        self,
        ticker: str,
        *,
        lookback_days: int = 30,
        limit: int = 10,
    ) -> dict[str, Any]:
        symbol = ticker.upper()
        cache_key = f"{self._cache_prefix}:{symbol}:{lookback_days}:{limit}"
        return await self._cached_load(
            operation="get_news_sentiment",
            cache_key=cache_key,
            ttl=60 * 30,
            loader=lambda: asyncio.to_thread(
                self._load_news_sentiment,
                symbol,
                lookback_days,
                limit,
            ),
        )

    def _load_news_sentiment(
        self,
        ticker: str,
        lookback_days: int,
        limit: int,
    ) -> dict[str, Any]:
        cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
        stock = yf.Ticker(ticker)
        raw_articles = stock.get_news(count=max(limit * 3, 12))

        articles: list[dict[str, Any]] = []
        for raw_article in raw_articles:
            article = normalize_news_article(raw_article)
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


class YahooFinanceAssetMetadataProvider(ProviderRuntimeMixin, AssetMetadataProvider):
    def __init__(self):
        super().__init__(
            domain="asset_metadata",
            provider_name="yfinance",
            cache_prefix="provider:metadata",
        )

    async def get_asset_metadata(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper()
        cache_key = f"{self._cache_prefix}:{symbol}"
        return await self._cached_load(
            operation="get_asset_metadata",
            cache_key=cache_key,
            ttl=60 * 60 * 6,
            loader=lambda: asyncio.to_thread(self._load_asset_metadata, symbol),
        )

    def _load_asset_metadata(self, ticker: str) -> dict[str, Any]:
        stock = yf.Ticker(ticker)
        info = getattr(stock, "fast_info", None) or {}
        return {
            "ticker": ticker,
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "timezone": info.get("timezone"),
            "quote_type": info.get("quoteType"),
        }
