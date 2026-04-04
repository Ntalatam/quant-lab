"""
Volatility-Targeted Trend Strategy.

Most strategies decide *whether* to be in a trade; this one decides *how much*
to risk on each trade.  Position size is the primary differentiator:

    position_weight = target_vol_pct / realized_vol_pct

So when volatility is high, positions shrink automatically — and when markets
are calm, more capital is deployed.  This produces equal risk contribution from
every position, regardless of how volatile the underlying is.

Additionally, a volatility circuit breaker closes ALL positions when realized
annualized volatility exceeds `vol_circuit_breaker` and blocks new entries until
vol normalizes.  This creates genuinely asymmetric behavior:
  - Calm markets  → full participation, vol-scaled size
  - Volatile markets → positions shrink or go to zero

The trend signal itself is a simple EMA crossover (fast > slow = bullish).

Risk math:
  realized_vol = std(daily_returns, vol_window) × sqrt(252) × 100  [annualized %]
  target_weight = min(target_vol_pct / realized_vol, max_position_per_ticker)

Parameters:
  fast_ema (10)               Fast EMA period for trend signal
  slow_ema  (30)              Slow EMA period for trend signal
  vol_window (21)             Lookback for realized volatility (trading days)
  target_vol_pct (15.0)       Target annualized vol per position (%)
  vol_circuit_breaker (40.0)  If realized vol > this, exit all and pause (%)
  max_position (0.5)          Hard cap on position weight per ticker
"""

from __future__ import annotations

import math

import pandas as pd

from app.strategies.base import BaseStrategy


class VolTargetTrend(BaseStrategy):
    name = "Volatility-Targeted Trend"
    description = (
        "Uses an EMA crossover for trend direction but sizes every position so "
        "it contributes equal realized risk. When market volatility spikes above "
        "the circuit-breaker level all positions are closed and new entries are "
        "blocked until volatility normalises. A systematic risk-first approach: "
        "each position carries constant risk regardless of asset volatility."
    )
    category = "risk_management"
    default_params = {
        "fast_ema": 10,
        "slow_ema": 30,
        "vol_window": 21,
        "target_vol_pct": 15.0,
        "vol_circuit_breaker": 40.0,
        "max_position": 0.5,
    }
    param_schema = [
        {
            "name": "fast_ema",
            "label": "Fast EMA Period",
            "type": "int",
            "default": 10,
            "min": 3,
            "max": 50,
            "step": 1,
            "description": "Short EMA for trend signal (fast > slow = bullish)",
        },
        {
            "name": "slow_ema",
            "label": "Slow EMA Period",
            "type": "int",
            "default": 30,
            "min": 10,
            "max": 200,
            "step": 1,
            "description": "Long EMA for trend signal",
        },
        {
            "name": "vol_window",
            "label": "Volatility Window (days)",
            "type": "int",
            "default": 21,
            "min": 5,
            "max": 63,
            "step": 1,
            "description": "Lookback for realized volatility estimate (~1 month default)",
        },
        {
            "name": "target_vol_pct",
            "label": "Target Volatility (%)",
            "type": "float",
            "default": 15.0,
            "min": 5.0,
            "max": 40.0,
            "step": 1.0,
            "description": "Annualized vol target per position. Lower = smaller positions in high-vol markets",
        },
        {
            "name": "vol_circuit_breaker",
            "label": "Vol Circuit Breaker (%)",
            "type": "float",
            "default": 40.0,
            "min": 20.0,
            "max": 100.0,
            "step": 5.0,
            "description": "If annualized realized vol exceeds this, exit all positions and pause entries",
        },
        {
            "name": "max_position",
            "label": "Max Position Per Ticker",
            "type": "float",
            "default": 0.5,
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "description": "Hard cap on any single ticker weight, regardless of vol target",
        },
    ]

    def __init__(
        self,
        fast_ema: int = 10,
        slow_ema: int = 30,
        vol_window: int = 21,
        target_vol_pct: float = 15.0,
        vol_circuit_breaker: float = 40.0,
        max_position: float = 0.5,
        **kwargs,
    ):
        self.fast_ema = int(fast_ema)
        self.slow_ema = int(slow_ema)
        self.vol_window = int(vol_window)
        self.target_vol_pct = float(target_vol_pct)
        self.vol_circuit_breaker = float(vol_circuit_breaker)
        self.max_position = float(max_position)

    @staticmethod
    def _realized_vol(close: pd.Series, window: int) -> float:
        """Annualized realized volatility (%) from daily returns."""
        if len(close) < window + 1:
            return 0.0
        daily_returns = close.pct_change().iloc[-window:]
        raw = float(daily_returns.std())
        return raw * math.sqrt(252) * 100.0

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals: dict[str, float] = {}
        min_bars = self.slow_ema + self.vol_window + 5

        for ticker, df in data.items():
            if len(df) < min_bars:
                signals[ticker] = 0.0
                continue

            close = df["adj_close"].astype(float)

            # ── Realized volatility ──
            realized_vol = self._realized_vol(close, self.vol_window)

            # ── Circuit breaker: vol too high → flat ──
            if realized_vol > self.vol_circuit_breaker:
                signals[ticker] = -1.0  # exit any existing position
                continue

            # ── Trend signal: fast EMA vs slow EMA ──
            ema_fast = close.ewm(span=self.fast_ema, adjust=False).mean()
            ema_slow = close.ewm(span=self.slow_ema, adjust=False).mean()
            bullish = float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1])

            if not bullish:
                signals[ticker] = -1.0
                continue

            # ── Volatility-scaled position size ──
            if realized_vol < 1.0:  # near-zero vol: cap at max_position
                weight = self.max_position
            else:
                weight = self.target_vol_pct / realized_vol

            weight = min(weight, self.max_position)
            signals[ticker] = weight

        return signals
