"""
Strategy registry — central lookup for all strategy classes.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_strategy import CustomStrategy
from app.services.custom_strategy import (
    build_custom_strategy_definition,
    list_custom_strategy_records,
    strategy_record_to_info,
)
from app.strategies.base import BaseStrategy
from app.strategies.donchian_breakout import DonchianBreakout
from app.strategies.macd_crossover import MACDCrossover
from app.strategies.market_neutral_momentum import MarketNeutralMomentum
from app.strategies.mean_reversion import MeanReversion
from app.strategies.ml_classifier import MLClassifier
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTrading
from app.strategies.rsi_mean_reversion import RSIMeanReversion
from app.strategies.sma_crossover import SMACrossover
from app.strategies.vol_target_trend import VolTargetTrend

STRATEGIES: dict[str, type[BaseStrategy]] = {
    "sma_crossover": SMACrossover,
    "mean_reversion": MeanReversion,
    "momentum": MomentumStrategy,
    "pairs_trading": PairsTrading,
    "market_neutral_momentum": MarketNeutralMomentum,
    "ml_classifier": MLClassifier,
    "rsi_mean_reversion": RSIMeanReversion,
    "macd_crossover": MACDCrossover,
    "donchian_breakout": DonchianBreakout,
    "vol_target_trend": VolTargetTrend,
}


def get_strategy_class(strategy_id: str) -> type[BaseStrategy]:
    if strategy_id not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_id}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[strategy_id]


def list_builtin_strategies() -> list[dict]:
    result = []
    for sid, cls in STRATEGIES.items():
        result.append(
            {
                "id": sid,
                "name": cls.name,
                "description": cls.description,
                "category": cls.category,
                "source_type": "builtin",
                "signal_mode": cls.signal_mode,
                "requires_short_selling": cls.requires_short_selling,
                "params": cls.param_schema,
            }
        )
    return result


async def list_strategies(db: AsyncSession | None = None) -> list[dict]:
    result = list_builtin_strategies()
    if db is None:
        return result
    custom = await list_custom_strategy_records(db)
    result.extend(strategy_record_to_info(item) for item in custom)
    return result


async def get_strategy_info(
    db: AsyncSession,
    strategy_id: str,
) -> dict:
    if strategy_id in STRATEGIES:
        strategy_cls = STRATEGIES[strategy_id]
        return {
            "id": strategy_id,
            "name": strategy_cls.name,
            "description": strategy_cls.description,
            "category": strategy_cls.category,
            "source_type": "builtin",
            "signal_mode": strategy_cls.signal_mode,
            "requires_short_selling": strategy_cls.requires_short_selling,
            "params": strategy_cls.param_schema,
            "defaults": strategy_cls.default_params,
        }

    custom = await db.get(CustomStrategy, strategy_id)
    if custom is None:
        raise ValueError(f"Unknown strategy: {strategy_id}")
    return {
        **strategy_record_to_info(custom),
        "defaults": custom.default_params,
    }


async def build_strategy_instance(
    db: AsyncSession,
    strategy_id: str,
    params: dict,
) -> BaseStrategy:
    if strategy_id in STRATEGIES:
        return STRATEGIES[strategy_id](**params)
    definition = await build_custom_strategy_definition(db, strategy_id)
    return definition.instantiate(params)
