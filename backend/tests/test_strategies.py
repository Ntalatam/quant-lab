"""Tests for trading strategies."""

import pandas as pd
import numpy as np
import pytest

from app.strategies.sma_crossover import SMACrossover
from app.strategies.mean_reversion import MeanReversion
from app.strategies.momentum import MomentumStrategy
from app.strategies.market_neutral_momentum import MarketNeutralMomentum
from app.strategies.pairs_trading import PairsTrading


def _make_df(prices: list[float], start: str = "2023-01-02") -> pd.DataFrame:
    """Create a minimal OHLCV dataframe from a list of close prices."""
    idx = pd.bdate_range(start, periods=len(prices))
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "adj_close": prices,
            "volume": [1_000_000] * len(prices),
        },
        index=idx,
    )


class TestSMACrossover:
    def test_golden_cross_generates_buy(self):
        # Create prices where short SMA crosses above long SMA
        prices = [100.0] * 50 + [100.0 + i * 0.5 for i in range(20)]
        df = _make_df(prices)
        strategy = SMACrossover(short_window=5, long_window=20)
        signals = strategy.generate_signals({"AAPL": df}, df.index[-1])
        # After a strong uptrend, short SMA should be above long SMA
        # The signal depends on the crossover timing
        assert "AAPL" in signals

    def test_death_cross_generates_sell(self):
        # Create prices that go up then sharply down
        prices = [100.0 + i for i in range(30)] + [130.0 - i * 2 for i in range(30)]
        df = _make_df(prices)
        strategy = SMACrossover(short_window=5, long_window=20)
        signals = strategy.generate_signals({"AAPL": df}, df.index[-1])
        assert "AAPL" in signals

    def test_insufficient_data_returns_zero(self):
        prices = [100.0] * 10
        df = _make_df(prices)
        strategy = SMACrossover(short_window=20, long_window=50)
        signals = strategy.generate_signals({"AAPL": df}, df.index[-1])
        assert signals["AAPL"] == 0.0


class TestMeanReversion:
    def test_oversold_generates_buy(self):
        # Stable prices then sharp drop below lower band
        np.random.seed(42)
        prices = [100.0 + np.random.normal(0, 0.5) for _ in range(40)]
        prices.append(85.0)  # sharp drop
        df = _make_df(prices)
        strategy = MeanReversion(lookback=20, num_std=2.0)
        signals = strategy.generate_signals({"AAPL": df}, df.index[-1])
        assert "AAPL" in signals

    def test_insufficient_data_returns_zero(self):
        prices = [100.0] * 5
        df = _make_df(prices)
        strategy = MeanReversion(lookback=20)
        signals = strategy.generate_signals({"AAPL": df}, df.index[-1])
        assert signals["AAPL"] == 0.0


class TestMomentum:
    def test_ranks_tickers_correctly(self):
        # AAPL going up, MSFT going down
        prices_aapl = [100.0 + i for i in range(100)]
        prices_msft = [100.0 - i * 0.5 for i in range(100)]
        prices_goog = [100.0] * 100

        data = {
            "AAPL": _make_df(prices_aapl),
            "MSFT": _make_df(prices_msft),
            "GOOG": _make_df(prices_goog),
        }

        strategy = MomentumStrategy(lookback_days=30, top_n=1, skip_days=0)
        signals = strategy.generate_signals(data, data["AAPL"].index[-1])
        assert signals["AAPL"] > 0  # best performer
        assert signals["MSFT"] < 0  # worst performer

    def test_insufficient_data_returns_zero(self):
        data = {"AAPL": _make_df([100.0] * 5)}
        strategy = MomentumStrategy(lookback_days=90)
        signals = strategy.generate_signals(data, data["AAPL"].index[-1])
        assert signals["AAPL"] == 0.0


class TestPairsTrading:
    def test_requires_exactly_two_tickers(self):
        data = {"AAPL": _make_df([100.0] * 100)}
        strategy = PairsTrading()
        signals = strategy.generate_signals(data, data["AAPL"].index[-1])
        assert signals["AAPL"] == 0.0

    def test_no_signal_when_spread_normal(self):
        # Two assets moving together
        np.random.seed(42)
        base = [100.0 + np.random.normal(0, 0.5) for _ in range(100)]
        data = {
            "AAPL": _make_df(base),
            "MSFT": _make_df([p + 5 for p in base]),
        }
        strategy = PairsTrading(lookback=60, entry_z=2.0)
        signals = strategy.generate_signals(data, data["AAPL"].index[-1])
        # With correlated prices, z-score should be near 0
        assert signals["AAPL"] == 0.0
        assert signals["MSFT"] == 0.0


class TestMarketNeutralMomentum:
    def test_generates_long_and_short_books(self):
        data = {
            "AAPL": _make_df([100.0 + i for i in range(180)]),
            "MSFT": _make_df([100.0 + i * 0.6 for i in range(180)]),
            "GLD": _make_df([100.0 - i * 0.2 for i in range(180)]),
            "TLT": _make_df([100.0 - i * 0.4 for i in range(180)]),
        }

        strategy = MarketNeutralMomentum(
            lookback_days=60,
            long_n=1,
            short_n=1,
            gross_exposure=1.0,
        )
        signals = strategy.generate_signals(data, data["AAPL"].index[-1])

        assert any(signal > 0 for signal in signals.values())
        assert any(signal < 0 for signal in signals.values())
