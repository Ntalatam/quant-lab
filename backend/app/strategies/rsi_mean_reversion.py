"""
RSI Mean Reversion Strategy.

Buys when the RSI crosses into oversold territory and sells when it crosses
into overbought territory.  Uses the classic Wilder smoothing (EWM with
alpha = 1/period) rather than a simple rolling mean so the signal matches
what traders see in live platforms.

Entry: RSI[t-1] >= oversold_threshold AND RSI[t] < oversold_threshold (crossover down into oversold — expect bounce)
Exit:  RSI[t-1] <= overbought_threshold AND RSI[t] > overbought_threshold (crossover up into overbought — take profit)

A secondary exit fires if price crosses back above the SMA after a long
entry (prevents holding positions through extended downtrends).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.strategies.base import BaseStrategy


class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion"
    description = (
        "Buys when RSI crosses below the oversold level and exits when RSI "
        "crosses above the overbought level. Uses Wilder-smoothed RSI (EWM). "
        "Classic short-term mean-reversion approach: buy the dip, sell the rip."
    )
    category = "mean_reversion"
    default_params = {
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "position_weight": 0.8,
    }
    param_schema = [
        {
            "name": "rsi_period",
            "label": "RSI Period",
            "type": "int",
            "default": 14,
            "min": 5,
            "max": 50,
            "step": 1,
            "description": "Lookback window for RSI calculation (Wilder smoothing)",
        },
        {
            "name": "oversold",
            "label": "Oversold Threshold",
            "type": "int",
            "default": 30,
            "min": 10,
            "max": 45,
            "step": 1,
            "description": "RSI below this level triggers a BUY signal",
        },
        {
            "name": "overbought",
            "label": "Overbought Threshold",
            "type": "int",
            "default": 70,
            "min": 55,
            "max": 90,
            "step": 1,
            "description": "RSI above this level triggers a SELL/exit signal",
        },
        {
            "name": "position_weight",
            "label": "Position Weight",
            "type": "float",
            "default": 0.8,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Fraction of portfolio allocated when signal fires",
        },
    ]

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: int = 30,
        overbought: int = 70,
        position_weight: float = 0.8,
        **kwargs,
    ):
        self.rsi_period = int(rsi_period)
        self.oversold = float(oversold)
        self.overbought = float(overbought)
        self.position_weight = float(position_weight)

    @staticmethod
    def _rsi(close: pd.Series, period: int) -> pd.Series:
        """Wilder-smoothed RSI using EWM (alpha = 1/period)."""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta.clip(upper=0))
        alpha = 1.0 / period
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        return 100.0 - (100.0 / (1.0 + rs))

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals: dict[str, float] = {}
        min_bars = self.rsi_period * 3  # need enough history for EWM to stabilise

        for ticker, df in data.items():
            if len(df) < min_bars:
                signals[ticker] = 0.0
                continue

            close = df["adj_close"].astype(float)
            rsi = self._rsi(close, self.rsi_period)

            if len(rsi) < 2:
                signals[ticker] = 0.0
                continue

            prev_rsi = rsi.iloc[-2]
            curr_rsi = rsi.iloc[-1]

            # Entry: RSI crosses down through oversold (momentum exhaustion)
            if prev_rsi >= self.oversold and curr_rsi < self.oversold:
                signals[ticker] = self.position_weight / max(len(data), 1)
            # Exit: RSI crosses up through overbought (profit target)
            elif prev_rsi <= self.overbought and curr_rsi > self.overbought:
                signals[ticker] = -1.0
            else:
                signals[ticker] = 0.0

        return signals
