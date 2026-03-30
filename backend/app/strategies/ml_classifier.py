"""
ML Classifier Strategy using XGBoost.

Trains a gradient-boosted classifier on technical indicators to predict
next-day return direction (up vs down). The model is trained once, on the
first ``train_pct`` fraction of available data for each ticker, so there is
no lookahead into the test / live-trading period.

Features used (all computed from price/volume history up to current bar):
  - 1-day, 5-day, 20-day momentum returns
  - Close / SMA-20, Close / SMA-50, SMA-20 / SMA-50 ratios
  - RSI (14)
  - ATR (14) as % of close price
  - Volume / SMA-20 volume ratio
  - Bollinger Band position (0 = lower band, 1 = upper band)

Target: 1 if next-day return > 0, else 0 (binary classification).

Signal convention:
  prob_up >= signal_threshold  → BUY  (positive weight signal)
  prob_up <= 1 - signal_threshold → SELL (−1 signal to flatten position)
  otherwise                   → HOLD (0)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.strategies.base import BaseStrategy


class MLClassifier(BaseStrategy):
    name = "ML Classifier (XGBoost)"
    description = (
        "Trains an XGBoost gradient-boosted classifier on 9 technical indicators "
        "(RSI, momentum, SMA ratio, ATR, volume ratio, Bollinger position) to "
        "predict next-day return direction. Model is trained on the first "
        "train_pct of available data with no lookahead into the test period."
    )
    category = "statistical_arbitrage"
    default_params = {
        "train_pct": 0.7,
        "n_estimators": 100,
        "max_depth": 4,
        "min_train_rows": 150,
        "signal_threshold": 0.55,
    }
    param_schema = [
        {
            "name": "train_pct",
            "label": "Train Fraction",
            "type": "float",
            "default": 0.7,
            "min": 0.4,
            "max": 0.85,
            "step": 0.05,
            "description": "Fraction of historical data used for training (rest is test)",
        },
        {
            "name": "n_estimators",
            "label": "Trees",
            "type": "int",
            "default": 100,
            "min": 20,
            "max": 500,
            "step": 10,
            "description": "Number of boosting rounds (more = slower but potentially better)",
        },
        {
            "name": "max_depth",
            "label": "Max Depth",
            "type": "int",
            "default": 4,
            "min": 2,
            "max": 8,
            "step": 1,
            "description": "Maximum tree depth (higher = more complex, prone to overfit)",
        },
        {
            "name": "min_train_rows",
            "label": "Min Training Rows",
            "type": "int",
            "default": 150,
            "min": 60,
            "max": 500,
            "step": 10,
            "description": "Minimum bars needed before the model is trained",
        },
        {
            "name": "signal_threshold",
            "label": "Signal Threshold",
            "type": "float",
            "default": 0.55,
            "min": 0.50,
            "max": 0.80,
            "step": 0.01,
            "description": "Minimum predicted probability to trigger a BUY or SELL",
        },
    ]

    def __init__(
        self,
        train_pct: float = 0.7,
        n_estimators: int = 100,
        max_depth: int = 4,
        min_train_rows: int = 150,
        signal_threshold: float = 0.55,
        **kwargs,
    ):
        self.train_pct = float(train_pct)
        self.n_estimators = int(n_estimators)
        self.max_depth = int(max_depth)
        self.min_train_rows = int(min_train_rows)
        self.signal_threshold = float(signal_threshold)
        # Per-ticker state (populated lazily on first call)
        self._models: dict = {}
        self._trained_on: dict[str, int] = {}  # ticker → row count at train time

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Build feature matrix from OHLCV DataFrame.

        All features use only past data (no shift(-1)), so calling this on the
        current bar is safe — no future prices leak in.
        """
        close = df["adj_close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float)

        feats = pd.DataFrame(index=df.index)

        # Momentum returns
        feats["ret_1d"] = close.pct_change(1)
        feats["ret_5d"] = close.pct_change(5)
        feats["ret_20d"] = close.pct_change(20)

        # SMA ratios
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        feats["close_sma20"] = close / sma20 - 1
        feats["close_sma50"] = close / sma50 - 1
        feats["sma20_sma50"] = sma20 / sma50 - 1

        # RSI (14)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        feats["rsi"] = (100 - (100 / (1 + rs))) / 100  # normalise to [0, 1]

        # ATR (14) as fraction of close
        tr = pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        feats["atr_pct"] = tr.rolling(14).mean() / (close + 1e-10)

        # Volume ratio
        vol_sma20 = volume.rolling(20).mean()
        feats["vol_ratio"] = volume / (vol_sma20 + 1e-10)

        # Bollinger Band position (0 = at lower, 1 = at upper, can exceed)
        bb_std = close.rolling(20).std()
        bb_upper = sma20 + 2 * bb_std
        bb_lower = sma20 - 2 * bb_std
        feats["bb_pos"] = (close - bb_lower) / (bb_upper - bb_lower + 1e-10)

        return feats.dropna()

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _train(self, df: pd.DataFrame, ticker: str) -> bool:
        """
        Train one XGBoost model for *ticker* using the first train_pct of *df*.
        Returns True if training succeeded.
        """
        try:
            import xgboost as xgb  # lazy import — optional dependency
        except ImportError:
            raise ImportError(
                "xgboost is required for the ML Classifier strategy. "
                "Install it with: pip install xgboost"
            )

        feats = self._compute_features(df)
        if len(feats) < self.min_train_rows:
            return False

        # Target: 1 if *next* day's return is positive (shift(-1) into future)
        # This is computed entirely within the training window, so no future leak
        # into the live-trading (test) period.
        next_ret = df["adj_close"].astype(float).pct_change(1).shift(-1)
        target = (next_ret > 0).astype(int)

        # Align features and target; drop the last row (no next-day label yet)
        common_idx = feats.index.intersection(target.dropna().index)
        feats = feats.loc[common_idx]
        target = target.loc[common_idx]

        n_train = int(len(feats) * self.train_pct)
        if n_train < 50:
            return False

        X_train = feats.iloc[:n_train].values.astype(np.float32)
        y_train = target.iloc[:n_train].values.astype(int)

        model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train, y_train)

        self._models[ticker] = model
        self._trained_on[ticker] = len(df)
        return True

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: dict[str, pd.DataFrame], current_date: pd.Timestamp
    ) -> dict[str, float]:
        signals: dict[str, float] = {}

        for ticker, df in data.items():
            if len(df) < self.min_train_rows:
                signals[ticker] = 0.0
                continue

            # Train lazily on first call with sufficient data
            if ticker not in self._models:
                trained = self._train(df, ticker)
                if not trained:
                    signals[ticker] = 0.0
                    continue

            model = self._models[ticker]

            # Features for the current bar (no future data)
            feats = self._compute_features(df)
            if feats.empty:
                signals[ticker] = 0.0
                continue

            latest = feats.iloc[-1:].values.astype(np.float32)
            prob_up: float = float(model.predict_proba(latest)[0, 1])

            if prob_up >= self.signal_threshold:
                # BUY — equal-weight across all tickers in universe
                signals[ticker] = 0.95 / max(len(data), 1)
            elif prob_up <= (1.0 - self.signal_threshold):
                # SELL — flatten any existing position
                signals[ticker] = -1.0
            else:
                signals[ticker] = 0.0  # hold

        return signals
