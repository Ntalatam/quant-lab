from __future__ import annotations

import asyncio
from datetime import date

import pandas as pd

from app.services.portfolio import Portfolio
from app.services.portfolio_optimizer import (
    PortfolioConstructionRequest,
    construct_target_weights,
)


def _frame(prices: list[float], volume: int = 1_000_000) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": prices,
            "high": [price * 1.01 for price in prices],
            "low": [price * 0.99 for price in prices],
            "close": prices,
            "adj_close": prices,
            "volume": [volume for _ in prices],
        }
    )


class TestPortfolioOptimizer:
    def test_equal_weight_construction_allocates_across_positive_views(self):
        portfolio = Portfolio(initial_capital=100_000)
        result = asyncio.run(
            construct_target_weights(
                PortfolioConstructionRequest(
                    raw_signals={"AAPL": 0.6, "MSFT": 0.3, "GOOG": -1.0},
                    data_window={
                        "AAPL": _frame([100 + i for i in range(80)]),
                        "MSFT": _frame([200 + i for i in range(80)]),
                        "GOOG": _frame([300 + i for i in range(80)]),
                    },
                    current_prices={"AAPL": 120.0, "MSFT": 220.0, "GOOG": 320.0},
                    portfolio=portfolio,
                    signal_mode="long_only",
                    construction_model="equal_weight",
                    max_position_pct=60,
                    max_gross_exposure_pct=100,
                    turnover_limit_pct=100,
                    max_sector_exposure_pct=100,
                )
            )
        )

        assert round(result.target_weights["AAPL"], 4) == 0.45
        assert round(result.target_weights["MSFT"], 4) == 0.45
        assert result.target_weights.get("GOOG", 0.0) == 0.0

    def test_risk_parity_tilts_toward_lower_volatility_asset(self):
        portfolio = Portfolio(initial_capital=100_000)
        low_vol = [100, 101, 100.5, 101.5, 101, 102] * 20
        high_vol = [100, 106, 99, 108, 97, 110] * 20

        result = asyncio.run(
            construct_target_weights(
                PortfolioConstructionRequest(
                    raw_signals={"AAPL": 0.5, "TSLA": 0.5},
                    data_window={
                        "AAPL": _frame(low_vol),
                        "TSLA": _frame(high_vol),
                    },
                    current_prices={"AAPL": 102.0, "TSLA": 110.0},
                    portfolio=portfolio,
                    signal_mode="long_only",
                    construction_model="risk_parity",
                    max_position_pct=80,
                    max_gross_exposure_pct=100,
                    turnover_limit_pct=100,
                    max_sector_exposure_pct=100,
                )
            )
        )

        assert result.target_weights["AAPL"] > result.target_weights["TSLA"]

    def test_turnover_limit_blends_toward_current_book(self):
        portfolio = Portfolio(initial_capital=100_000)
        portfolio.execute_buy("AAPL", 500, 100.0, 0.0, 0.0, date(2024, 1, 2))
        portfolio.update_prices({"AAPL": 100.0}, date(2024, 1, 2))

        result = asyncio.run(
            construct_target_weights(
                PortfolioConstructionRequest(
                    raw_signals={"AAPL": 0.0},
                    data_window={"AAPL": _frame([100 + i for i in range(80)])},
                    current_prices={"AAPL": 100.0},
                    portfolio=portfolio,
                    signal_mode="long_short",
                    construction_model="equal_weight",
                    max_position_pct=60,
                    max_gross_exposure_pct=100,
                    turnover_limit_pct=10,
                    max_sector_exposure_pct=100,
                    allow_short_selling=True,
                )
            )
        )

        assert result.turnover_pct == 10
        assert 0 < result.target_weights["AAPL"] < 0.5
