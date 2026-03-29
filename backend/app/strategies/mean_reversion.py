"""
Bollinger Band Mean Reversion Strategy.

Buys when price drops below the lower Bollinger Band (oversold),
sells when price rises above the upper band (overbought).
Works best in range-bound markets.
"""

import pandas as pd

from app.strategies.base import BaseStrategy


class MeanReversion(BaseStrategy):
    name = "Mean Reversion (Bollinger Bands)"
    description = (
        "Buys when price drops below the lower Bollinger Band and sells when "
        "it rises above the upper band. Profits from the tendency of prices "
        "to revert to their mean."
    )
    category = "mean_reversion"
    default_params = {"lookback": 20, "num_std": 2.0, "position_weight": 0.3}
    param_schema = [
        {
            "name": "lookback",
            "label": "Lookback Period",
            "type": "int",
            "default": 20,
            "min": 10,
            "max": 100,
            "step": 1,
            "description": "Window for computing the moving average and standard deviation",
        },
        {
            "name": "num_std",
            "label": "Std Deviations",
            "type": "float",
            "default": 2.0,
            "min": 0.5,
            "max": 4.0,
            "step": 0.1,
            "description": "Number of standard deviations for the Bollinger Bands",
        },
        {
            "name": "position_weight",
            "label": "Position Weight",
            "type": "float",
            "default": 0.3,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Target portfolio weight per position",
        },
    ]

    def __init__(
        self,
        lookback: int = 20,
        num_std: float = 2.0,
        position_weight: float = 0.3,
        **kwargs,
    ):
        self.lookback = int(lookback)
        self.num_std = float(num_std)
        self.position_weight = float(position_weight)

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals = {}
        for ticker, df in data.items():
            if len(df) < self.lookback + 1:
                signals[ticker] = 0.0
                continue

            close = df["adj_close"]
            sma = close.rolling(self.lookback).mean()
            std = close.rolling(self.lookback).std()

            upper = sma + (std * self.num_std)
            lower = sma - (std * self.num_std)

            current_price = close.iloc[-1]
            prev_price = close.iloc[-2]

            if current_price < lower.iloc[-1] and prev_price >= lower.iloc[-2]:
                # Price crossed below lower band — buy (oversold)
                signals[ticker] = self.position_weight / max(len(data), 1)
            elif current_price > upper.iloc[-1] and prev_price <= upper.iloc[-2]:
                # Price crossed above upper band — sell (overbought)
                signals[ticker] = -1.0
            elif current_price > sma.iloc[-1] and prev_price <= sma.iloc[-2]:
                # Crossed above mean — take partial profits
                signals[ticker] = -0.5
            else:
                signals[ticker] = 0.0

        return signals
