"""
Donchian Channel Breakout (Turtle Trading System 1).

Based on the famous Turtle Trading experiment by Richard Dennis and Bill Eckhardt.
The rules are simple:

Entry:  Buy when today's close exceeds the highest close of the last `entry_period` bars.
        (N-day channel breakout — price makes a new N-day high)

Exit:   Sell when today's close falls below the lowest close of the last `exit_period` bars.
        (Shorter exit window to lock in profits faster than the entry trigger)

Position sizing is equal weight across all triggered tickers, capped at max_position.

This captures sustained trends while avoiding whipsaws by requiring a genuine
multi-week breakout before entry.  The asymmetric entry/exit windows (20-day in,
10-day out) mirror the original Turtle System 1 parameters.
"""

from __future__ import annotations

import pandas as pd

from app.strategies.base import BaseStrategy


class DonchianBreakout(BaseStrategy):
    name = "Donchian Channel Breakout"
    description = (
        "Buys on a new N-day high breakout (Turtle System 1). Exits when price "
        "falls below the M-day low channel. Replicates the core logic of the "
        "famous Turtle Trading experiment: ride big trends, cut losers quickly "
        "with the shorter exit window."
    )
    category = "trend_following"
    default_params = {
        "entry_period": 20,
        "exit_period": 10,
        "position_weight": 0.9,
    }
    param_schema = [
        {
            "name": "entry_period",
            "label": "Entry Channel (days)",
            "type": "int",
            "default": 20,
            "min": 5,
            "max": 120,
            "step": 1,
            "description": "Buy when close exceeds highest close of last N days (Turtle: 20)",
        },
        {
            "name": "exit_period",
            "label": "Exit Channel (days)",
            "type": "int",
            "default": 10,
            "min": 3,
            "max": 60,
            "step": 1,
            "description": "Sell when close falls below lowest close of last M days (Turtle: 10). Should be < entry_period.",
        },
        {
            "name": "position_weight",
            "label": "Position Weight",
            "type": "float",
            "default": 0.9,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Total portfolio weight allocated across all active positions",
        },
    ]

    def __init__(
        self,
        entry_period: int = 20,
        exit_period: int = 10,
        position_weight: float = 0.9,
        **kwargs,
    ):
        self.entry_period = int(entry_period)
        self.exit_period = int(exit_period)
        self.position_weight = float(position_weight)
        # Track which tickers are currently in a position
        self._in_position: dict[str, bool] = {}

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals: dict[str, float] = {}
        min_bars = self.entry_period + 1

        for ticker, df in data.items():
            if ticker not in self._in_position:
                self._in_position[ticker] = False

            if len(df) < min_bars:
                signals[ticker] = 0.0
                continue

            close = df["adj_close"].astype(float)

            # Donchian entry channel: highest close over last entry_period bars
            # Use .iloc[-entry_period-1:-1] so we don't include today's close
            entry_high = close.iloc[-(self.entry_period + 1):-1].max()
            # Donchian exit channel: lowest close over last exit_period bars
            exit_low = close.iloc[-(self.exit_period + 1):-1].min()

            current_close = close.iloc[-1]

            currently_in = self._in_position[ticker]

            if not currently_in and current_close > entry_high:
                # Breakout entry
                self._in_position[ticker] = True
                signals[ticker] = self.position_weight / max(len(data), 1)
            elif currently_in and current_close < exit_low:
                # Exit: price broke below exit channel
                self._in_position[ticker] = False
                signals[ticker] = -1.0
            elif currently_in:
                # Still in position — hold (positive weight maintains existing pos)
                signals[ticker] = self.position_weight / max(len(data), 1)
            else:
                signals[ticker] = 0.0

        return signals
