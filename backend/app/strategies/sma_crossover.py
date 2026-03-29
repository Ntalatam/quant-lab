"""
Dual Simple Moving Average Crossover Strategy.

BUY on golden cross (short SMA > long SMA), SELL on death cross.
Classic trend-following baseline strategy.
"""

import pandas as pd

from app.strategies.base import BaseStrategy


class SMACrossover(BaseStrategy):
    name = "SMA Crossover"
    description = (
        "Buys when the short-term moving average crosses above the long-term "
        "moving average (golden cross) and sells on the inverse (death cross). "
        "Classic trend-following approach."
    )
    category = "trend_following"
    default_params = {"short_window": 20, "long_window": 50, "position_weight": 0.95}
    param_schema = [
        {
            "name": "short_window",
            "label": "Short SMA Period",
            "type": "int",
            "default": 20,
            "min": 5,
            "max": 100,
            "step": 1,
            "description": "Number of days for the fast-moving average",
        },
        {
            "name": "long_window",
            "label": "Long SMA Period",
            "type": "int",
            "default": 50,
            "min": 10,
            "max": 300,
            "step": 5,
            "description": "Number of days for the slow-moving average",
        },
        {
            "name": "position_weight",
            "label": "Position Weight",
            "type": "float",
            "default": 0.95,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Target portfolio weight when fully invested",
        },
    ]

    def __init__(
        self,
        short_window: int = 20,
        long_window: int = 50,
        position_weight: float = 0.95,
        **kwargs,
    ):
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self.position_weight = float(position_weight)

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals = {}
        for ticker, df in data.items():
            if len(df) < self.long_window + 1:
                signals[ticker] = 0.0
                continue

            close = df["adj_close"]
            sma_short = close.rolling(self.short_window).mean()
            sma_long = close.rolling(self.long_window).mean()

            if sma_short.isna().iloc[-1] or sma_long.isna().iloc[-1]:
                signals[ticker] = 0.0
                continue

            short_above = sma_short.iloc[-1] > sma_long.iloc[-1]
            prev_short_above = sma_short.iloc[-2] > sma_long.iloc[-2]

            if short_above and not prev_short_above:
                signals[ticker] = self.position_weight / max(len(data), 1)
            elif not short_above and prev_short_above:
                signals[ticker] = -1.0
            else:
                signals[ticker] = 0.0

        return signals
