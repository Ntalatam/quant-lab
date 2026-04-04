from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.api import strategies as strategies_api
from app.services.custom_strategy import (
    CustomStrategyValidationError,
    build_custom_strategy_definition,
    create_custom_strategy,
    validate_custom_strategy_source,
)

VALID_STRATEGY = """
STRATEGY = {
    "name": "Custom RSI Dip Buyer",
    "description": "Buys oversold names and exits when RSI recovers.",
    "category": "mean_reversion",
    "signal_mode": "long_only",
    "requires_short_selling": False,
    "params": [
        {
            "name": "rsi_window",
            "label": "RSI Window",
            "type": "int",
            "default": 14,
            "min": 5,
            "max": 30,
            "step": 1,
            "description": "RSI lookback.",
        },
        {
            "name": "entry_level",
            "label": "Entry Level",
            "type": "float",
            "default": 35.0,
            "min": 5.0,
            "max": 50.0,
            "step": 1.0,
            "description": "Oversold threshold.",
        },
    ],
}


def generate_signals(data, current_date, tickers, params):
    signals = {}
    for ticker in tickers:
        strength = latest(rsi(close(data, ticker), params["rsi_window"]))
        signals[ticker] = 1.0 if strength < params["entry_level"] else 0.0
    return signals
"""

INVALID_STRATEGY = """
import os

STRATEGY = {
    "name": "Unsafe",
    "description": "Should fail.",
    "category": "momentum",
    "signal_mode": "long_only",
    "params": [],
}


def generate_signals(data, current_date, tickers, params):
    return {"AAPL": 1.0}
"""


class _FakeConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _statement):
        return 1


class _HealthyEngine:
    def connect(self):
        return _FakeConnection()


class _FakePaperManager:
    def __init__(self, *_args, **_kwargs):
        pass

    async def resume_active_sessions(self):
        return None

    async def shutdown(self):
        return None

    def health_summary(self):
        return {
            "runtime_sessions": 0,
            "subscriber_channels": 0,
        }


async def _noop():
    return None


def _build_price_frame(prices: list[float]) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=len(prices))
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


def _build_client(monkeypatch, db):
    async def _get_db_override():
        yield db

    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", _HealthyEngine())
    app = app_main.create_app()
    app.dependency_overrides[strategies_api.get_db] = _get_db_override
    return TestClient(app)


def test_validate_custom_strategy_source_extracts_schema():
    result = validate_custom_strategy_source(VALID_STRATEGY)

    assert result["valid"] is True
    assert result["preview"]["name"] == "Custom RSI Dip Buyer"
    assert result["preview"]["source_type"] == "custom"
    assert result["extracted"]["defaults"]["rsi_window"] == 14
    assert result["extracted"]["params"][1]["name"] == "entry_level"


def test_validate_custom_strategy_source_rejects_unsafe_imports():
    with pytest.raises(CustomStrategyValidationError, match="Import"):
        validate_custom_strategy_source(INVALID_STRATEGY)


@pytest.mark.asyncio
async def test_custom_strategy_definition_executes_against_market_data(db):
    record = await create_custom_strategy(db, VALID_STRATEGY)
    await db.commit()
    await db.refresh(record)

    definition = await build_custom_strategy_definition(db, record.id)
    strategy = definition.instantiate({"entry_level": 45.0})
    data = {
        "AAPL": _build_price_frame([100.0 - i * 0.6 for i in range(40)]),
        "MSFT": _build_price_frame([100.0 + i * 0.2 for i in range(40)]),
    }

    signals = strategy.generate_signals(data, data["AAPL"].index[-1])

    assert set(signals) == {"AAPL", "MSFT"}
    assert all(-1.0 <= signal <= 1.0 for signal in signals.values())


def test_custom_strategy_routes_persist_and_serve_editor_payload(monkeypatch, db):
    with _build_client(monkeypatch, db) as client:
        validate_response = client.post(
            "/api/strategies/custom/validate",
            json={"code": VALID_STRATEGY},
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        create_response = client.post(
            "/api/strategies/custom",
            json={"code": VALID_STRATEGY},
        )
        assert create_response.status_code == 200
        created = create_response.json()
        strategy_id = created["id"]
        assert strategy_id.startswith("custom_")
        assert created["code"].strip().startswith("STRATEGY =")

        list_response = client.get("/api/strategies/custom")
        assert list_response.status_code == 200
        assert any(item["id"] == strategy_id for item in list_response.json())

        params_response = client.get(f"/api/strategies/{strategy_id}/params")
        assert params_response.status_code == 200
        params_payload = params_response.json()
        assert params_payload["source_type"] == "custom"
        assert params_payload["defaults"]["entry_level"] == 35.0

        editor_spec = client.get("/api/strategies/custom/editor-spec")
        assert editor_spec.status_code == 200
        assert "template" in editor_spec.json()
