from __future__ import annotations

import pandas as pd
import pytest

from app.services.custom_strategy import (
    clamp,
    close,
    create_custom_strategy,
    crosses_above,
    crosses_below,
    delete_custom_strategy,
    get_editor_spec,
    highest,
    latest,
    list_custom_strategy_records,
    lowest,
    pct_change,
    previous,
    strategy_record_to_detail,
    strategy_record_to_summary,
    top_n,
    update_custom_strategy,
    validate_custom_strategy_source,
    volume,
)
from app.services.strategy_registry import (
    build_strategy_instance,
    get_strategy_class,
    get_strategy_info,
    list_builtin_strategies,
    list_strategies,
)
from app.strategies.sma_crossover import SMACrossover

VALID_CUSTOM_STRATEGY = """
STRATEGY = {
    "name": "Custom Trend Rotation",
    "description": "Owns the strongest names by simple momentum.",
    "category": "momentum",
    "signal_mode": "long_only",
    "requires_short_selling": False,
    "params": [
        {
            "name": "lookback",
            "label": "Lookback",
            "type": "int",
            "default": 20,
            "min": 5,
            "max": 100,
            "step": 1,
            "description": "Momentum lookback window.",
        }
    ],
}


def generate_signals(data, current_date, tickers, params):
    scores = {}
    for ticker in tickers:
        scores[ticker] = momentum(close(data, ticker), params["lookback"])
    leaders = top_n(scores, 1)
    return {ticker: 1.0 if ticker in leaders else 0.0 for ticker in tickers}
"""

UPDATED_CUSTOM_STRATEGY = """
STRATEGY = {
    "name": "Custom Mean Reverter",
    "description": "Fades names that stretch too far from trend.",
    "category": "mean_reversion",
    "signal_mode": "long_short",
    "requires_short_selling": True,
    "params": [
        {
            "name": "window",
            "label": "Window",
            "type": "int",
            "default": 10,
            "min": 5,
            "max": 40,
            "step": 1,
            "description": "Mean-reversion lookback window.",
        }
    ],
}


def generate_signals(data, current_date, tickers, params):
    signals = {}
    for ticker in tickers:
        series = close(data, ticker)
        score = latest(zscore(series, params["window"]))
        signals[ticker] = clamp(-score, -1.0, 1.0)
    return signals
"""

WARNING_STRATEGY = """
STRATEGY = {
    "name": "Auto Short Required",
    "description": "Declares long_short without the explicit short flag.",
    "category": "stat_arb",
    "signal_mode": "long_short",
    "params": [],
}


def generate_signals(data, current_date, tickers, params):
    return {ticker: 0.0 for ticker in tickers}
"""


def _build_market_frame(prices: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=len(prices))
    size = len(prices)
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "adj_close": prices,
            "volume": volumes or [1_000_000 + i * 10_000 for i in range(size)],
        },
        index=idx,
    )


@pytest.mark.asyncio
async def test_strategy_registry_lists_builtin_and_custom_strategies(db):
    record = await create_custom_strategy(db, VALID_CUSTOM_STRATEGY)
    await db.commit()
    await db.refresh(record)

    builtin = list_builtin_strategies()
    merged_without_db = await list_strategies()
    merged_with_db = await list_strategies(db)

    assert any(item["id"] == "sma_crossover" for item in builtin)
    assert len(merged_without_db) == len(builtin)
    assert any(
        item["id"] == record.id and item["source_type"] == "custom" for item in merged_with_db
    )

    builtin_info = await get_strategy_info(db, "sma_crossover")
    custom_info = await get_strategy_info(db, record.id)

    assert builtin_info["source_type"] == "builtin"
    assert builtin_info["defaults"]["short_window"] == SMACrossover.default_params["short_window"]
    assert custom_info["source_type"] == "custom"
    assert custom_info["defaults"]["lookback"] == 20

    with pytest.raises(ValueError, match="Unknown strategy"):
        get_strategy_class("does_not_exist")
    with pytest.raises(ValueError, match="Unknown strategy"):
        await get_strategy_info(db, "does_not_exist")


@pytest.mark.asyncio
async def test_build_strategy_instance_supports_builtin_and_custom_sources(db):
    record = await create_custom_strategy(db, VALID_CUSTOM_STRATEGY)
    await db.commit()
    await db.refresh(record)

    builtin = await build_strategy_instance(
        db,
        "sma_crossover",
        {"short_window": 5, "long_window": 10, "position_weight": 0.8},
    )
    custom = await build_strategy_instance(db, record.id, {"lookback": 15})

    market_data = {
        "AAPL": _build_market_frame([100 + i for i in range(30)]),
        "MSFT": _build_market_frame([120 + i * 0.3 for i in range(30)]),
    }
    timestamp = next(iter(market_data.values())).index[-1]

    builtin_signals = builtin.generate_signals(market_data, timestamp)
    custom_signals = custom.generate_signals(market_data, timestamp)

    assert isinstance(builtin, SMACrossover)
    assert set(builtin_signals) == {"AAPL", "MSFT"}
    assert set(custom_signals) == {"AAPL", "MSFT"}
    assert sum(value > 0 for value in custom_signals.values()) == 1


@pytest.mark.asyncio
async def test_custom_strategy_crud_helpers_and_serializers(db):
    record = await create_custom_strategy(db, VALID_CUSTOM_STRATEGY)
    await db.commit()
    await db.refresh(record)

    detail = strategy_record_to_detail(record)
    summary = strategy_record_to_summary(record)
    assert detail["code"].strip().startswith("STRATEGY =")
    assert summary["id"] == record.id

    updated = await update_custom_strategy(db, record, UPDATED_CUSTOM_STRATEGY)
    await db.commit()
    await db.refresh(updated)

    records = await list_custom_strategy_records(db)
    assert records[0].id == record.id
    assert records[0].signal_mode == "long_short"
    assert records[0].requires_short_selling is True

    await delete_custom_strategy(db, updated)
    await db.commit()

    assert await list_custom_strategy_records(db) == []


def test_custom_strategy_editor_helpers_cover_common_utility_flows():
    editor_spec = get_editor_spec()
    helper_names = {helper["name"] for helper in editor_spec["helpers"]}
    assert {"close", "volume", "zscore", "top_n", "clamp"}.issubset(helper_names)

    raw_data = {
        "AAPL": {
            "adj_close": [100.0, 102.0, 101.0, 105.0],
            "volume": [1_000_000, 1_100_000, 1_050_000, 1_200_000],
        },
        "MSFT": {
            "adj_close": [200.0, 198.0, 199.0, 197.0],
            "volume": [900_000, 920_000, 940_000, 960_000],
        },
    }

    aapl_close = close(raw_data, "AAPL")
    aapl_volume = volume(raw_data, "AAPL")

    assert latest(aapl_close) == 105.0
    assert previous(aapl_close) == 101.0
    assert highest(aapl_close, 3) == 105.0
    assert lowest(aapl_close, 3) == 101.0
    assert latest(aapl_volume) == 1_200_000.0
    assert pct_change(aapl_close, 1)[-1] > 0
    assert crosses_above([1.0, 2.0], [1.5, 1.8]) is True
    assert crosses_below([2.0, 1.0], [1.5, 1.2]) is True
    assert top_n({"AAPL": 0.5, "MSFT": 0.2}, 1) == ["AAPL"]
    assert clamp(1.7, -1.0, 1.0) == 1.0


def test_validate_custom_strategy_source_surfaces_long_short_warning():
    result = validate_custom_strategy_source(WARNING_STRATEGY)

    assert result["valid"] is True
    assert result["preview"]["requires_short_selling"] is True
    assert any("short-selling support" in warning for warning in result["warnings"])
