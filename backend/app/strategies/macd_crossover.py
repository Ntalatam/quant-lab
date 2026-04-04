"""
MACD Crossover Strategy.

The MACD (Moving Average Convergence/Divergence) is one of the most widely
used momentum indicators.  This strategy generates:

  BUY  when the MACD line crosses above the signal line (histogram goes positive)
  SELL when the MACD line crosses below the signal line (histogram goes negative)

MACD line   = EMA(fast) − EMA(slow)
Signal line = EMA(MACD, signal_period)
Histogram   = MACD − Signal

Position size scales with |histogram| normalized to recent histogram range so
larger momentum crossovers get proportionally more capital.
"""

from __future__ import annotations

import pandas as pd

from app.strategies.base import BaseStrategy


class MACDCrossover(BaseStrategy):
    name = "MACD Crossover"
    description = (
        "Buys when the MACD line crosses above its signal line and exits "
        "when it crosses below. Position size scales with histogram magnitude "
        "— stronger momentum crossovers deploy more capital. "
        "Widely used trend-following / momentum approach."
    )
    category = "trend_following"
    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "position_weight": 0.95,
    }
    param_schema = [
        {
            "name": "fast_period",
            "label": "Fast EMA Period",
            "type": "int",
            "default": 12,
            "min": 3,
            "max": 50,
            "step": 1,
            "description": "Short-term EMA period (standard: 12)",
        },
        {
            "name": "slow_period",
            "label": "Slow EMA Period",
            "type": "int",
            "default": 26,
            "min": 10,
            "max": 200,
            "step": 1,
            "description": "Long-term EMA period (standard: 26)",
        },
        {
            "name": "signal_period",
            "label": "Signal Period",
            "type": "int",
            "default": 9,
            "min": 3,
            "max": 30,
            "step": 1,
            "description": "EMA period applied to the MACD line (standard: 9)",
        },
        {
            "name": "position_weight",
            "label": "Max Position Weight",
            "type": "float",
            "default": 0.95,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Maximum portfolio weight allocated on a full signal",
        },
    ]

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        position_weight: float = 0.95,
        **kwargs,
    ):
        self.fast_period = int(fast_period)
        self.slow_period = int(slow_period)
        self.signal_period = int(signal_period)
        self.position_weight = float(position_weight)

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals: dict[str, float] = {}
        min_bars = self.slow_period + self.signal_period + 5

        for ticker, df in data.items():
            if len(df) < min_bars:
                signals[ticker] = 0.0
                continue

            close = df["adj_close"].astype(float)
            ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
            ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
            histogram = macd_line - signal_line

            if len(histogram) < 2:
                signals[ticker] = 0.0
                continue

            prev_hist = histogram.iloc[-2]
            curr_hist = histogram.iloc[-1]

            # Bullish crossover: histogram crosses zero from below
            if prev_hist <= 0 and curr_hist > 0:
                # Scale position with histogram strength (cap at 1)
                recent_abs = histogram.abs().rolling(50).max().iloc[-1]
                strength = min(abs(curr_hist) / (recent_abs + 1e-10), 1.0)
                weight = self.position_weight * (0.5 + 0.5 * strength)
                signals[ticker] = weight / max(len(data), 1)
            # Bearish crossover: histogram crosses zero from above
            elif prev_hist >= 0 and curr_hist < 0:
                signals[ticker] = -1.0
            else:
                signals[ticker] = 0.0

        return signals
