"""
Market-neutral long/short momentum strategy.

Ranks the universe by trailing return, then buys the strongest names and shorts
the weakest names with matched gross exposure on each side.
"""

import pandas as pd

from app.strategies.base import BaseStrategy


class MarketNeutralMomentum(BaseStrategy):
    name = "Market-Neutral Momentum"
    description = (
        "Ranks the universe by trailing return, buys the strongest names, and "
        "shorts the weakest names with matched gross exposure for a "
        "market-neutral momentum book."
    )
    category = "momentum"
    signal_mode = "long_short"
    requires_short_selling = True
    default_params = {
        "lookback_days": 120,
        "skip_days": 5,
        "long_n": 3,
        "short_n": 3,
        "gross_exposure": 1.2,
    }
    param_schema = [
        {
            "name": "lookback_days",
            "label": "Lookback (Days)",
            "type": "int",
            "default": 120,
            "min": 20,
            "max": 365,
            "step": 5,
            "description": "Period used to rank trailing momentum",
        },
        {
            "name": "skip_days",
            "label": "Skip Recent Days",
            "type": "int",
            "default": 5,
            "min": 0,
            "max": 30,
            "step": 1,
            "description": "Skip recent bars to reduce short-term reversal noise",
        },
        {
            "name": "long_n",
            "label": "Long Book Size",
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "Number of strongest names to hold long",
        },
        {
            "name": "short_n",
            "label": "Short Book Size",
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "Number of weakest names to hold short",
        },
        {
            "name": "gross_exposure",
            "label": "Gross Exposure",
            "type": "float",
            "default": 1.2,
            "min": 0.4,
            "max": 2.0,
            "step": 0.05,
            "description": "Total gross exposure across long and short books",
        },
    ]

    def __init__(
        self,
        lookback_days: int = 120,
        skip_days: int = 5,
        long_n: int = 3,
        short_n: int = 3,
        gross_exposure: float = 1.2,
        **kwargs,
    ):
        self.lookback_days = int(lookback_days)
        self.skip_days = int(skip_days)
        self.long_n = int(long_n)
        self.short_n = int(short_n)
        self.gross_exposure = float(gross_exposure)

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        scores: dict[str, float] = {}

        for ticker, df in data.items():
            if len(df) < self.lookback_days + self.skip_days:
                continue

            close = df["adj_close"]
            end_idx = len(close) - 1 - self.skip_days
            start_idx = end_idx - self.lookback_days
            if start_idx < 0 or end_idx < 0:
                continue

            scores[ticker] = (close.iloc[end_idx] / close.iloc[start_idx]) - 1

        if len(scores) < max(self.long_n, self.short_n):
            return {ticker: 0.0 for ticker in data}

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        long_count = min(self.long_n, len(ranked))
        short_count = min(self.short_n, max(len(ranked) - long_count, 0))
        if long_count == 0 or short_count == 0:
            return {ticker: 0.0 for ticker in data}

        long_tickers = {ticker for ticker, _ in ranked[:long_count]}
        short_tickers = {ticker for ticker, _ in ranked[-short_count:]}
        side_gross = self.gross_exposure / 2
        long_weight = side_gross / long_count
        short_weight = -(side_gross / short_count)

        signals: dict[str, float] = {}
        for ticker in data:
            if ticker in long_tickers:
                signals[ticker] = long_weight
            elif ticker in short_tickers:
                signals[ticker] = short_weight
            else:
                signals[ticker] = 0.0
        return signals
