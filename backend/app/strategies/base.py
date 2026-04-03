"""
Abstract base class for all trading strategies.

Signal convention:
  long_only mode:
    Positive float (0 to 1): BUY with that fraction as target portfolio weight
    Negative float (-1 to 0): SELL that fraction of existing long position
    0: HOLD / no action

  long_short mode:
    Positive float (0 to 1): target long portfolio weight
    Negative float (-1 to 0): target short portfolio weight
    0: target flat / no action
"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    name: str = "Base Strategy"
    description: str = ""
    category: str = "other"
    default_params: dict = {}
    param_schema: list[dict] = []
    signal_mode: str = "long_only"
    requires_short_selling: bool = False

    @abstractmethod
    def generate_signals(
        self,
        data: dict[str, pd.DataFrame],
        current_date: pd.Timestamp,
    ) -> dict[str, float]:
        """
        Generate trading signals for each ticker.

        Args:
            data: Dict mapping ticker -> DataFrame of OHLCV data
                  up to and including current_date (no future data).
            current_date: The current simulation date.

        Returns:
            Dict mapping ticker -> signal value.
        """
        pass
