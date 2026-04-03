"""
Strategy registry — central lookup for all strategy classes.
"""

from app.strategies.base import BaseStrategy
from app.strategies.sma_crossover import SMACrossover
from app.strategies.mean_reversion import MeanReversion
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTrading
from app.strategies.market_neutral_momentum import MarketNeutralMomentum
from app.strategies.ml_classifier import MLClassifier
from app.strategies.rsi_mean_reversion import RSIMeanReversion
from app.strategies.macd_crossover import MACDCrossover
from app.strategies.donchian_breakout import DonchianBreakout
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
                "signal_mode": cls.signal_mode,
                "requires_short_selling": cls.requires_short_selling,
                "params": cls.param_schema,
            }
        )
    return result
