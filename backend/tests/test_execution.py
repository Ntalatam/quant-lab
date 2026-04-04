"""Tests for the execution simulator."""

from app.services.execution import simulate_fill


class TestSimulateFill:
    def test_buy_slippage_increases_price(self):
        fill = simulate_fill(
            side="BUY",
            shares=100,
            bar_open=100.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=102.0,
            bar_volume=100_000,
            slippage_bps=10.0,
            commission_per_share=0.005,
            market_impact_model="constant",
        )
        assert fill.filled
        assert fill.fill_price > 100.0  # slippage raises buy price

    def test_sell_slippage_decreases_price(self):
        fill = simulate_fill(
            side="SELL",
            shares=100,
            bar_open=100.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=98.0,
            bar_volume=100_000,
            slippage_bps=10.0,
            commission_per_share=0.005,
            market_impact_model="constant",
        )
        assert fill.filled
        assert fill.fill_price < 100.0  # slippage lowers sell price

    def test_volume_constraint(self):
        fill = simulate_fill(
            side="BUY",
            shares=10_000,
            bar_open=100.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=102.0,
            bar_volume=1_000,
            slippage_bps=5.0,
            commission_per_share=0.005,
            market_impact_model="constant",
            max_volume_participation=0.05,
        )
        assert fill.filled
        assert fill.shares_filled <= 50  # 5% of 1000

    def test_zero_volume_rejects_order(self):
        fill = simulate_fill(
            side="BUY",
            shares=100,
            bar_open=100.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=102.0,
            bar_volume=0,
            slippage_bps=5.0,
            commission_per_share=0.005,
            market_impact_model="constant",
        )
        assert not fill.filled

    def test_commission_computed_correctly(self):
        fill = simulate_fill(
            side="BUY",
            shares=100,
            bar_open=100.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=102.0,
            bar_volume=100_000,
            slippage_bps=5.0,
            commission_per_share=0.01,
            market_impact_model="constant",
        )
        assert abs(fill.commission - (fill.shares_filled * 0.01)) < 0.001

    def test_fill_price_clamped_to_high(self):
        fill = simulate_fill(
            side="BUY",
            shares=100,
            bar_open=104.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=102.0,
            bar_volume=100_000,
            slippage_bps=500.0,  # very high slippage
            commission_per_share=0,
            market_impact_model="constant",
        )
        assert fill.fill_price <= 105.0

    def test_fill_price_clamped_to_low(self):
        fill = simulate_fill(
            side="SELL",
            shares=100,
            bar_open=96.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=98.0,
            bar_volume=100_000,
            slippage_bps=500.0,
            commission_per_share=0,
            market_impact_model="constant",
        )
        assert fill.fill_price >= 95.0

    def test_zero_slippage(self):
        fill = simulate_fill(
            side="BUY",
            shares=100,
            bar_open=100.0,
            bar_high=105.0,
            bar_low=95.0,
            bar_close=102.0,
            bar_volume=100_000,
            slippage_bps=0.0,
            commission_per_share=0.0,
            market_impact_model="constant",
        )
        assert fill.fill_price == 100.0
        assert fill.slippage_cost == 0.0

    def test_almgren_chriss_model_populates_cost_breakdown(self):
        fill = simulate_fill(
            side="BUY",
            shares=2_000,
            bar_open=100.0,
            bar_high=103.0,
            bar_low=99.0,
            bar_close=102.0,
            bar_volume=20_000,
            slippage_bps=5.0,
            commission_per_share=0.005,
            market_impact_model="almgren_chriss",
            max_volume_participation=0.05,
        )
        assert fill.filled
        assert fill.spread_cost > 0
        assert fill.market_impact_cost > 0
        assert fill.timing_cost >= 0
        assert fill.implementation_shortfall >= fill.commission + fill.spread_cost
