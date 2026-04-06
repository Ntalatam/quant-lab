from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.models.paper import PaperTradingSession
from app.services.brokers.alpaca import AlpacaPaperBrokerAdapter
from app.services.brokers.paper import SimulatedPaperBrokerAdapter
from app.services.portfolio import Portfolio


def _build_session(**overrides) -> PaperTradingSession:
    payload = {
        "id": "paper-session-1",
        "name": "Paper Session",
        "status": "active",
        "execution_mode": "simulated_paper",
        "broker_adapter": "paper",
        "strategy_id": "sma_crossover",
        "strategy_params": {"short_window": 20, "long_window": 60},
        "tickers": ["AAPL"],
        "benchmark": "SPY",
        "bar_interval": "1m",
        "polling_interval_seconds": 60,
        "initial_capital": 100_000.0,
        "slippage_bps": 5.0,
        "commission_per_share": 0.005,
        "market_impact_model": "almgren_chriss",
        "max_volume_participation_pct": 5.0,
        "portfolio_construction_model": "equal_weight",
        "portfolio_lookback_days": 63,
        "max_position_pct": 25.0,
        "max_gross_exposure_pct": 150.0,
        "turnover_limit_pct": 100.0,
        "max_sector_exposure_pct": 100.0,
        "allow_short_selling": False,
        "max_short_position_pct": 25.0,
        "short_margin_requirement_pct": 50.0,
        "short_borrow_rate_bps": 200.0,
        "short_locate_fee_bps": 10.0,
        "short_squeeze_threshold_pct": 15.0,
        "cash": 100_000.0,
        "market_value": 0.0,
        "total_equity": 100_000.0,
        "total_return_pct": 0.0,
    }
    payload.update(overrides)
    return PaperTradingSession(**payload)


@pytest.mark.asyncio
async def test_simulated_paper_adapter_executes_and_updates_portfolio():
    adapter = SimulatedPaperBrokerAdapter()
    session = _build_session()
    runtime = SimpleNamespace(
        portfolio=Portfolio(initial_capital=session.initial_capital, cash=session.cash)
    )
    snapshot_time = datetime(2026, 4, 5, 14, 30)
    current_prices = {"AAPL": 100.0}
    current_bars = {
        "AAPL": {
            "open": 100.0,
            "high": 101.0,
            "low": 99.5,
            "close": 100.5,
            "volume": 10_000,
        }
    }

    synced = await adapter.execute_target_weights(
        session,
        runtime,
        target_weights={"AAPL": 0.25},
        current_bars=current_bars,
        current_prices=current_prices,
        snapshot_time=snapshot_time,
        db=None,
    )

    assert synced.account_label == "Local simulator"
    assert synced.open_order_count == 0
    assert len(synced.orders) == 1
    assert synced.orders[0].ticker == "AAPL"
    assert synced.orders[0].status in {"filled", "partial"}
    assert len(synced.executions) == 1
    assert synced.executions[0].ticker == "AAPL"
    assert runtime.portfolio is not None
    assert "AAPL" in runtime.portfolio.positions
    assert runtime.portfolio.positions["AAPL"].shares > 0


@pytest.mark.asyncio
async def test_alpaca_adapter_syncs_account_state_from_http_api(monkeypatch):
    monkeypatch.setattr(settings, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(settings, "ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/account":
            return httpx.Response(
                200,
                json={
                    "account_number": "PA12345678",
                    "cash": "52000.00",
                    "buying_power": "104000.00",
                },
            )
        if request.url.path == "/v2/positions":
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "AAPL",
                        "qty": "120",
                        "avg_entry_price": "188.40",
                        "current_price": "192.10",
                    }
                ],
            )
        if request.url.path == "/v2/orders":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "alpaca-order-1",
                        "client_order_id": "quantlab-paper-1-abc123",
                        "symbol": "AAPL",
                        "side": "buy",
                        "qty": "120",
                        "filled_qty": "120",
                        "filled_avg_price": "192.10",
                        "status": "filled",
                        "type": "market",
                        "time_in_force": "day",
                        "submitted_at": "2026-04-05T14:30:00Z",
                        "updated_at": "2026-04-05T14:30:05Z",
                    },
                    {
                        "id": "alpaca-order-2",
                        "client_order_id": "quantlab-paper-1-def456",
                        "symbol": "MSFT",
                        "side": "buy",
                        "qty": "50",
                        "filled_qty": "0",
                        "status": "new",
                        "type": "market",
                        "time_in_force": "day",
                        "submitted_at": "2026-04-05T14:30:10Z",
                        "updated_at": "2026-04-05T14:30:12Z",
                    },
                    {
                        "id": "external-order",
                        "client_order_id": "outside-session",
                        "symbol": "SPY",
                        "side": "buy",
                        "qty": "10",
                        "filled_qty": "10",
                        "filled_avg_price": "500.00",
                        "status": "filled",
                        "type": "market",
                        "time_in_force": "day",
                        "submitted_at": "2026-04-05T14:00:00Z",
                        "updated_at": "2026-04-05T14:00:05Z",
                    },
                ],
            )
        raise AssertionError(f"Unexpected Alpaca request: {request.method} {request.url}")

    adapter = AlpacaPaperBrokerAdapter(transport=httpx.MockTransport(handler))
    session = _build_session(
        execution_mode="broker_paper",
        broker_adapter="alpaca",
        id="paper-1",
    )
    runtime = SimpleNamespace(portfolio=None)

    synced = await adapter.sync_account_state(
        session,
        runtime,
        current_prices={"AAPL": 192.1},
        snapshot_time=datetime(2026, 4, 5, 14, 31),
        db=None,
    )

    assert synced.account_label == "Alpaca paper • 5678"
    assert synced.open_order_count == 1
    assert len(synced.orders) == 2
    assert {order.ticker for order in synced.orders} == {"AAPL", "MSFT"}
    assert len(synced.executions) == 1
    assert synced.executions[0].broker_execution_id is not None
    assert runtime.portfolio is not None
    assert runtime.portfolio.cash == pytest.approx(52_000.0)
    assert runtime.portfolio.positions["AAPL"].shares == 120
