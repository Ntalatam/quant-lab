"""Tests for the Portfolio class."""

from datetime import date

from app.services.portfolio import Portfolio, Position


class TestPortfolio:
    def test_initial_state(self):
        p = Portfolio(initial_capital=100_000)
        assert p.cash == 100_000
        assert p.total_equity == 100_000
        assert p.market_value == 0
        assert len(p.positions) == 0
        assert len(p.trade_log) == 0

    def test_buy_reduces_cash(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_buy("AAPL", 100, 150.0, commission=0.50, slippage_cost=1.0, trade_date=date(2024, 1, 2))
        expected_cost = (150.0 * 100) + 0.50 + 1.0
        assert abs(p.cash - (100_000 - expected_cost)) < 0.01
        assert "AAPL" in p.positions
        assert p.positions["AAPL"].shares == 100

    def test_sell_adds_proceeds(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_buy("AAPL", 100, 150.0, 0.50, 1.0, date(2024, 1, 2))
        cash_after_buy = p.cash
        p.execute_sell("AAPL", 100, 160.0, 0.50, 1.0, date(2024, 1, 10))
        expected_proceeds = (160.0 * 100) - 0.50 - 1.0
        assert abs(p.cash - (cash_after_buy + expected_proceeds)) < 0.01
        assert "AAPL" not in p.positions

    def test_cannot_buy_more_than_cash(self):
        p = Portfolio(initial_capital=1_000)
        p.execute_buy("AAPL", 100, 150.0, 0.50, 1.0, date(2024, 1, 2))
        # Should buy fewer shares than requested
        assert p.positions["AAPL"].shares < 100
        assert p.cash >= 0

    def test_cannot_sell_nonexistent_position(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_sell("AAPL", 100, 150.0, 0.50, 1.0, date(2024, 1, 2))
        assert len(p.trade_log) == 0

    def test_partial_sell(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_buy("AAPL", 100, 150.0, 0, 0, date(2024, 1, 2))
        p.execute_sell("AAPL", 50, 160.0, 0, 0, date(2024, 1, 10))
        assert p.positions["AAPL"].shares == 50

    def test_avg_cost_basis_on_multiple_buys(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_buy("AAPL", 100, 100.0, 0, 0, date(2024, 1, 2))
        p.execute_buy("AAPL", 100, 200.0, 0, 0, date(2024, 1, 3))
        assert p.positions["AAPL"].shares == 200
        assert abs(p.positions["AAPL"].avg_cost - 150.0) < 0.01

    def test_equity_matches_cash_plus_market_value(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_buy("AAPL", 100, 150.0, 0, 0, date(2024, 1, 2))
        p.update_prices({"AAPL": 160.0}, date(2024, 1, 3))
        expected = p.cash + (100 * 160.0)
        assert abs(p.total_equity - expected) < 0.01

    def test_trade_log_records_correctly(self):
        p = Portfolio(initial_capital=100_000)
        p.execute_buy("AAPL", 50, 150.0, 0.50, 1.0, date(2024, 1, 2))
        p.execute_sell("AAPL", 50, 160.0, 0.50, 1.0, date(2024, 1, 10))
        assert len(p.trade_log) == 2
        buy = p.trade_log[0]
        sell = p.trade_log[1]
        assert buy.side == "BUY"
        assert sell.side == "SELL"
        assert sell.pnl is not None
        assert sell.pnl > 0

    def test_exposure_pct(self):
        p = Portfolio(initial_capital=100_000)
        assert p.exposure_pct == 0
        p.execute_buy("AAPL", 100, 150.0, 0, 0, date(2024, 1, 2))
        p.update_prices({"AAPL": 150.0}, date(2024, 1, 2))
        assert p.exposure_pct > 0


class TestPosition:
    def test_market_value(self):
        pos = Position(ticker="AAPL", shares=100, avg_cost=150.0, entry_date=date(2024, 1, 1), current_price=160.0)
        assert pos.market_value == 16000.0

    def test_unrealized_pnl(self):
        pos = Position(ticker="AAPL", shares=100, avg_cost=150.0, entry_date=date(2024, 1, 1), current_price=160.0)
        assert pos.unrealized_pnl == 1000.0

    def test_unrealized_pnl_pct(self):
        pos = Position(ticker="AAPL", shares=100, avg_cost=100.0, entry_date=date(2024, 1, 1), current_price=110.0)
        assert abs(pos.unrealized_pnl_pct - 10.0) < 0.01
