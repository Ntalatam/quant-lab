from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.services.providers.base import (
    AssetMetadataProvider,
    EarningsDataProvider,
    EconomicDataProvider,
    MarketDataProvider,
    NewsSentimentProvider,
)
from app.services.providers.fred import FredEconomicDataProvider
from app.services.providers.yfinance import (
    YahooFinanceAssetMetadataProvider,
    YahooFinanceEarningsProvider,
    YahooFinanceMarketDataProvider,
    YahooFinanceNewsSentimentProvider,
)


@dataclass
class ProviderRegistry:
    market_data: MarketDataProvider
    economic_data: EconomicDataProvider
    earnings_data: EarningsDataProvider
    news_sentiment: NewsSentimentProvider
    asset_metadata: AssetMetadataProvider

    def status_payload(self) -> list[dict[str, str | None]]:
        return [
            self.market_data.status_snapshot(),
            self.economic_data.status_snapshot(),
            self.earnings_data.status_snapshot(),
            self.news_sentiment.status_snapshot(),
            self.asset_metadata.status_snapshot(),
        ]


_provider_registry: ProviderRegistry | None = None


def _build_provider_registry() -> ProviderRegistry:
    if settings.MARKET_DATA_PROVIDER != "yfinance":
        raise ValueError(f"Unsupported market data provider: {settings.MARKET_DATA_PROVIDER}")
    if settings.ECONOMIC_DATA_PROVIDER != "fred":
        raise ValueError(f"Unsupported economic data provider: {settings.ECONOMIC_DATA_PROVIDER}")
    if settings.EARNINGS_DATA_PROVIDER != "yfinance":
        raise ValueError(f"Unsupported earnings data provider: {settings.EARNINGS_DATA_PROVIDER}")
    if settings.NEWS_SENTIMENT_PROVIDER != "yfinance":
        raise ValueError(f"Unsupported news sentiment provider: {settings.NEWS_SENTIMENT_PROVIDER}")
    if settings.ASSET_METADATA_PROVIDER != "yfinance":
        raise ValueError(f"Unsupported asset metadata provider: {settings.ASSET_METADATA_PROVIDER}")

    return ProviderRegistry(
        market_data=YahooFinanceMarketDataProvider(),
        economic_data=FredEconomicDataProvider(),
        earnings_data=YahooFinanceEarningsProvider(),
        news_sentiment=YahooFinanceNewsSentimentProvider(),
        asset_metadata=YahooFinanceAssetMetadataProvider(),
    )


def get_provider_registry() -> ProviderRegistry:
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = _build_provider_registry()
    return _provider_registry


def set_provider_registry(registry: ProviderRegistry | None):
    global _provider_registry
    _provider_registry = registry
