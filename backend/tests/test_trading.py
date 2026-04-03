from datetime import date

import pandas as pd

from app.services.portfolio import Portfolio
from app.services.trading import execute_signals


def _bar(price: float, volume: int = 1_000_000) -> pd.Series:
    return pd.Series(
        {
            "open": price,
            "high": price * 1.01,
            "low": price * 0.99,
            "close": price,
            "volume": volume,
        }
    )


class TestExecuteSignals:
    def test_buy_signal_opens_position(self):
        portfolio = Portfolio(initial_capital=100_000)
        executions = execute_signals(
            portfolio=portfolio,
            signals={"AAPL": 0.5},
            current_bars={"AAPL": _bar(100)},
            current_prices={"AAPL": 100},
            max_position_pct=50,
            slippage_bps=0,
            commission_per_share=0,
            trade_date=date(2024, 1, 2),
        )

        assert executions[0].status == "filled"
        assert "AAPL" in portfolio.positions
        assert portfolio.positions["AAPL"].shares > 0

    def test_sell_signal_closes_existing_position(self):
        portfolio = Portfolio(initial_capital=100_000)
        portfolio.execute_buy("AAPL", 100, 100, 0, 0, date(2024, 1, 2))

        executions = execute_signals(
            portfolio=portfolio,
            signals={"AAPL": -1.0},
            current_bars={"AAPL": _bar(110)},
            current_prices={"AAPL": 110},
            max_position_pct=50,
            slippage_bps=0,
            commission_per_share=0,
            trade_date=date(2024, 1, 3),
        )

        assert executions[0].status == "filled"
        assert "AAPL" not in portfolio.positions

    def test_hold_like_signal_is_skipped_if_position_already_at_target(self):
        portfolio = Portfolio(initial_capital=100_000)
        portfolio.execute_buy("AAPL", 500, 100, 0, 0, date(2024, 1, 2))
        portfolio.update_prices({"AAPL": 100}, date(2024, 1, 2))

        executions = execute_signals(
            portfolio=portfolio,
            signals={"AAPL": 0.5},
            current_bars={"AAPL": _bar(100)},
            current_prices={"AAPL": 100},
            max_position_pct=50,
            slippage_bps=0,
            commission_per_share=0,
            trade_date=date(2024, 1, 3),
        )

        assert executions[0].status == "skipped"
        assert executions[0].reason.startswith("Signal did not increase exposure")

    def test_long_short_signal_opens_short_position(self):
        portfolio = Portfolio(initial_capital=100_000)
        executions = execute_signals(
            portfolio=portfolio,
            signals={"AAPL": -0.25},
            current_bars={"AAPL": _bar(100)},
            current_prices={"AAPL": 100},
            max_position_pct=50,
            slippage_bps=0,
            commission_per_share=0,
            trade_date=date(2024, 1, 2),
            signal_mode="long_short",
            allow_short_selling=True,
            max_short_position_pct=30,
            short_margin_requirement_pct=50,
            short_locate_fee_bps=0,
        )

        assert executions[0].status == "filled"
        assert portfolio.positions["AAPL"].shares < 0

    def test_negative_signal_in_long_only_mode_does_not_open_short(self):
        portfolio = Portfolio(initial_capital=100_000)
        executions = execute_signals(
            portfolio=portfolio,
            signals={"AAPL": -1.0},
            current_bars={"AAPL": _bar(100)},
            current_prices={"AAPL": 100},
            max_position_pct=50,
            slippage_bps=0,
            commission_per_share=0,
            trade_date=date(2024, 1, 2),
        )

        assert executions[0].status == "skipped"
        assert "AAPL" not in portfolio.positions
