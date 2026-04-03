"""
Statistical Pairs Trading Strategy.

Trades the mean-reverting spread between two correlated assets.
Uses the log price ratio z-score for entry/exit signals.
Requires exactly 2 tickers.
"""

import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy


class PairsTrading(BaseStrategy):
    name = "Statistical Pairs Trading"
    description = (
        "Trades the mean-reverting spread between two correlated assets. "
        "Goes long the underperformer and short the outperformer when the "
        "spread diverges beyond a z-score threshold."
    )
    category = "statistical_arbitrage"
    signal_mode = "long_short"
    requires_short_selling = True
    default_params = {
        "lookback": 60,
        "entry_z": 2.0,
        "exit_z": 0.5,
        "position_weight": 0.4,
    }
    param_schema = [
        {
            "name": "lookback",
            "label": "Lookback Period",
            "type": "int",
            "default": 60,
            "min": 20,
            "max": 252,
            "step": 5,
            "description": "Window for computing the spread's mean and std deviation",
        },
        {
            "name": "entry_z",
            "label": "Entry Z-Score",
            "type": "float",
            "default": 2.0,
            "min": 1.0,
            "max": 4.0,
            "step": 0.1,
            "description": "Z-score threshold to enter a trade",
        },
        {
            "name": "exit_z",
            "label": "Exit Z-Score",
            "type": "float",
            "default": 0.5,
            "min": 0.0,
            "max": 2.0,
            "step": 0.1,
            "description": "Z-score threshold to exit (close to mean)",
        },
        {
            "name": "position_weight",
            "label": "Position Weight",
            "type": "float",
            "default": 0.4,
            "min": 0.1,
            "max": 0.5,
            "step": 0.05,
            "description": "Portfolio weight per leg of the pair",
        },
    ]

    def __init__(
        self,
        lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        position_weight: float = 0.4,
        **kwargs,
    ):
        self.lookback = int(lookback)
        self.entry_z = float(entry_z)
        self.exit_z = float(exit_z)
        self.position_weight = float(position_weight)
        self._in_trade = False
        self._trade_direction = None

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        tickers = list(data.keys())
        if len(tickers) != 2:
            return {t: 0.0 for t in tickers}

        ticker_a, ticker_b = tickers[0], tickers[1]
        df_a, df_b = data[ticker_a], data[ticker_b]

        if len(df_a) < self.lookback or len(df_b) < self.lookback:
            return {t: 0.0 for t in tickers}

        price_a = df_a["adj_close"].iloc[-self.lookback :]
        price_b = df_b["adj_close"].iloc[-self.lookback :]

        aligned = pd.DataFrame({"a": price_a, "b": price_b}).dropna()
        if len(aligned) < self.lookback * 0.8:
            return {t: 0.0 for t in tickers}

        spread = np.log(aligned["a"] / aligned["b"])
        z_score = (spread.iloc[-1] - spread.mean()) / max(spread.std(), 1e-8)

        signals = {ticker_a: 0.0, ticker_b: 0.0}

        if not self._in_trade:
            if z_score > self.entry_z:
                # A is expensive, B is cheap — short A, long B
                signals[ticker_a] = -1.0
                signals[ticker_b] = self.position_weight
                self._in_trade = True
                self._trade_direction = "short_spread"
            elif z_score < -self.entry_z:
                # A is cheap, B is expensive — long A, short B
                signals[ticker_a] = self.position_weight
                signals[ticker_b] = -1.0
                self._in_trade = True
                self._trade_direction = "long_spread"
        else:
            if abs(z_score) < self.exit_z:
                # Spread reverted — exit both
                signals[ticker_a] = -1.0
                signals[ticker_b] = -1.0
                self._in_trade = False
                self._trade_direction = None

        return signals
