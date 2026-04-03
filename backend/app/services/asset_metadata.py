from __future__ import annotations

import asyncio
from functools import lru_cache

import yfinance as yf


_SECTOR_OVERRIDES = {
    "SPY": "Broad Market ETF",
    "QQQ": "Broad Market ETF",
    "IWM": "Broad Market ETF",
    "DIA": "Broad Market ETF",
    "TLT": "Rates ETF",
    "GLD": "Commodity ETF",
    "SLV": "Commodity ETF",
    "USO": "Commodity ETF",
    "XLB": "Materials",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Healthcare",
    "XLY": "Consumer Discretionary",
    "XLC": "Communication Services",
}


@lru_cache(maxsize=512)
def _lookup_sector_sync(ticker: str) -> str | None:
    normalized = ticker.strip().upper()
    if not normalized:
        return None
    if normalized in _SECTOR_OVERRIDES:
        return _SECTOR_OVERRIDES[normalized]

    try:
        info = yf.Ticker(normalized).info or {}
    except Exception:
        info = {}

    for key in ("sectorDisp", "sector", "category"):
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


async def get_ticker_sectors(tickers: list[str]) -> dict[str, str | None]:
    normalized = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))
    if not normalized:
        return {}

    tasks = [asyncio.to_thread(_lookup_sector_sync, ticker) for ticker in normalized]
    resolved = await asyncio.gather(*tasks, return_exceptions=True)

    sector_map: dict[str, str | None] = {}
    for ticker, sector in zip(normalized, resolved):
        sector_map[ticker] = sector if isinstance(sector, str) else None
    return sector_map
