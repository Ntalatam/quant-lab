"""
Strategy registry — central lookup for all strategy classes.
"""

from app.strategies.base import BaseStrategy
from app.strategies.sma_crossover import SMACrossover
from app.strategies.mean_reversion import MeanReversion
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTrading

STRATEGIES: dict[str, type[BaseStrategy]] = {
    "sma_crossover": SMACrossover,
    "mean_reversion": MeanReversion,
    "momentum": MomentumStrategy,
    "pairs_trading": PairsTrading,
}


def get_strategy_class(strategy_id: str) -> type[BaseStrategy]:
    if strategy_id not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy: {strategy_id}. Available: {list(STRATEGIES.keys())}"
        )
    return STRATEGIES[strategy_id]


def list_strategies() -> list[dict]:
    result = []
    for sid, cls in STRATEGIES.items():
        result.append(
            {
                "id": sid,
                "name": cls.name,
                "description": cls.description,
                "category": cls.category,
                "params": cls.param_schema,
            }
        )
    return result
