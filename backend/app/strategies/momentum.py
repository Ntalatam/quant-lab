"""
Cross-Sectional Momentum Strategy.

Ranks all tickers by trailing return over a lookback period.
Goes long the top performers, exits the bottom performers.
Relative (cross-sectional) momentum, not absolute.
"""

import pandas as pd

from app.strategies.base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    name = "Cross-Sectional Momentum"
    description = (
        "Ranks tickers by trailing returns and holds the top performers. "
        "Rotates out of losers and into winners on each rebalance."
    )
    category = "momentum"
    default_params = {
        "lookback_days": 90,
        "top_n": 3,
        "skip_days": 5,
        "position_weight": 0.9,
    }
    param_schema = [
        {
            "name": "lookback_days",
            "label": "Lookback (Days)",
            "type": "int",
            "default": 90,
            "min": 20,
            "max": 365,
            "step": 5,
            "description": "Period over which to measure momentum",
        },
        {
            "name": "top_n",
            "label": "Top N Holdings",
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "Number of top-momentum tickers to hold",
        },
        {
            "name": "skip_days",
            "label": "Skip Recent Days",
            "type": "int",
            "default": 5,
            "min": 0,
            "max": 30,
            "step": 1,
            "description": "Skip most recent N days to avoid short-term reversal",
        },
        {
            "name": "position_weight",
            "label": "Total Weight",
            "type": "float",
            "default": 0.9,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Total portfolio weight allocated to momentum picks",
        },
    ]

    def __init__(
        self,
        lookback_days: int = 90,
        top_n: int = 3,
        skip_days: int = 5,
        position_weight: float = 0.9,
        **kwargs,
    ):
        self.lookback_days = int(lookback_days)
        self.top_n = int(top_n)
        self.skip_days = int(skip_days)
        self.position_weight = float(position_weight)

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        scores = {}
        for ticker, df in data.items():
            if len(df) < self.lookback_days + self.skip_days:
                continue

            close = df["adj_close"]
            end_idx = len(close) - 1 - self.skip_days
            start_idx = end_idx - self.lookback_days

            if start_idx < 0 or end_idx < 0:
                continue

            ret = (close.iloc[end_idx] / close.iloc[start_idx]) - 1
            scores[ticker] = ret

        if not scores:
            return {t: 0.0 for t in data}

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_tickers = {t for t, _ in ranked[: self.top_n]}

        signals = {}
        weight_per = self.position_weight / self.top_n

        for ticker in data:
            if ticker in top_tickers:
                signals[ticker] = weight_per
            else:
                signals[ticker] = -1.0

        return signals
