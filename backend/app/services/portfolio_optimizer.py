from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.services.asset_metadata import get_ticker_sectors
from app.services.portfolio import Portfolio

SUPPORTED_CONSTRUCTION_MODELS = {
    "equal_weight",
    "risk_parity",
    "mean_variance",
    "black_litterman",
    "kelly",
}


@dataclass
class PortfolioConstructionRequest:
    raw_signals: dict[str, float]
    data_window: dict[str, pd.DataFrame]
    current_prices: dict[str, float]
    portfolio: Portfolio
    signal_mode: str = "long_only"
    construction_model: str = "equal_weight"
    lookback_days: int = 63
    max_position_pct: float = 25.0
    max_short_position_pct: float = 25.0
    max_gross_exposure_pct: float = 150.0
    turnover_limit_pct: float = 100.0
    max_sector_exposure_pct: float = 100.0
    allow_short_selling: bool = False


@dataclass
class PortfolioConstructionResult:
    target_weights: dict[str, float]
    turnover_pct: float
    gross_exposure_pct: float
    sector_exposure_pct: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


async def construct_target_weights(
    request: PortfolioConstructionRequest,
) -> PortfolioConstructionResult:
    model = _normalize_model(request.construction_model)
    warnings: list[str] = []
    if model != request.construction_model:
        warnings.append(
            f"Construction model '{request.construction_model}' was mapped to '{model}'."
        )

    current_weights = _current_weights(request.portfolio, request.current_prices)
    base_targets = (
        _build_long_short_targets(request, current_weights, model, warnings)
        if request.signal_mode == "long_short"
        else _build_long_only_targets(request, current_weights, model, warnings)
    )

    capped_targets = await _apply_sector_limits(
        weights=_apply_gross_cap(base_targets, request.max_gross_exposure_pct),
        max_sector_exposure_pct=request.max_sector_exposure_pct,
        warnings=warnings,
    )
    final_targets, turnover_pct = _apply_turnover_limit(
        current_weights=current_weights,
        target_weights=capped_targets,
        turnover_limit_pct=request.turnover_limit_pct,
    )
    sector_exposure_pct = _summarize_sector_exposure(capped_targets)

    return PortfolioConstructionResult(
        target_weights=_clean_weights(final_targets),
        turnover_pct=round(turnover_pct, 2),
        gross_exposure_pct=round(sum(abs(weight) for weight in final_targets.values()) * 100, 2),
        sector_exposure_pct=sector_exposure_pct,
        warnings=warnings,
    )


def _normalize_model(model: str) -> str:
    normalized = (model or "equal_weight").strip().lower()
    if normalized == "kelly":
        return "mean_variance"
    if normalized in SUPPORTED_CONSTRUCTION_MODELS:
        return normalized
    return "equal_weight"


def _build_long_only_targets(
    request: PortfolioConstructionRequest,
    current_weights: dict[str, float],
    model: str,
    warnings: list[str],
) -> dict[str, float]:
    targets = {ticker: max(weight, 0.0) for ticker, weight in current_weights.items() if weight > 0}
    positive_signals = {
        ticker: signal for ticker, signal in request.raw_signals.items() if signal > 0
    }

    for ticker, signal in request.raw_signals.items():
        if signal >= 0:
            continue
        existing = max(targets.get(ticker, 0.0), 0.0)
        if existing <= 0:
            targets[ticker] = 0.0
            continue
        reduction = min(abs(signal), 1.0)
        targets[ticker] = existing * (1 - reduction)

    preserved_gross = sum(
        weight for ticker, weight in targets.items() if ticker not in positive_signals
    )
    gross_cap = max(request.max_gross_exposure_pct / 100, 0.0)
    available_gross = max(gross_cap - preserved_gross, 0.0)
    desired_long_gross = min(sum(positive_signals.values()), available_gross)
    if desired_long_gross <= 0 or not positive_signals:
        return targets

    allocated = _allocate_side(
        tickers=list(positive_signals.keys()),
        view_strengths=positive_signals,
        data_window=request.data_window,
        model=model,
        gross_target=desired_long_gross,
        per_asset_cap=request.max_position_pct / 100,
        lookback_days=request.lookback_days,
        warnings=warnings,
    )
    targets.update(allocated)
    return targets


def _build_long_short_targets(
    request: PortfolioConstructionRequest,
    current_weights: dict[str, float],
    model: str,
    warnings: list[str],
) -> dict[str, float]:
    universe = set(current_weights) | set(request.raw_signals)
    targets = {ticker: 0.0 for ticker in universe}

    long_views = {ticker: signal for ticker, signal in request.raw_signals.items() if signal > 0}
    short_views = {
        ticker: abs(signal)
        for ticker, signal in request.raw_signals.items()
        if signal < 0 and request.allow_short_selling
    }

    gross_cap = max(request.max_gross_exposure_pct / 100, 0.0)
    desired_long_gross = sum(long_views.values())
    desired_short_gross = sum(short_views.values())
    total_desired_gross = desired_long_gross + desired_short_gross
    scale = min(gross_cap / total_desired_gross, 1.0) if total_desired_gross > 0 else 0.0

    if long_views:
        targets.update(
            _allocate_side(
                tickers=list(long_views.keys()),
                view_strengths=long_views,
                data_window=request.data_window,
                model=model,
                gross_target=desired_long_gross * scale,
                per_asset_cap=request.max_position_pct / 100,
                lookback_days=request.lookback_days,
                warnings=warnings,
            )
        )
    if short_views:
        short_allocations = _allocate_side(
            tickers=list(short_views.keys()),
            view_strengths=short_views,
            data_window=request.data_window,
            model=model,
            gross_target=desired_short_gross * scale,
            per_asset_cap=request.max_short_position_pct / 100,
            lookback_days=request.lookback_days,
            warnings=warnings,
        )
        targets.update({ticker: -weight for ticker, weight in short_allocations.items()})

    return targets


def _allocate_side(
    tickers: list[str],
    view_strengths: dict[str, float],
    data_window: dict[str, pd.DataFrame],
    model: str,
    gross_target: float,
    per_asset_cap: float,
    lookback_days: int,
    warnings: list[str],
) -> dict[str, float]:
    if gross_target <= 0 or not tickers:
        return {ticker: 0.0 for ticker in tickers}

    returns = _build_returns_frame(data_window, tickers, lookback_days)
    if model != "equal_weight" and returns.empty:
        warnings.append(
            f"{model} fell back to equal weight because there was not enough return history."
        )
        model = "equal_weight"

    if model == "equal_weight":
        raw_weights = np.ones(len(tickers))
    elif model == "risk_parity":
        vol = returns.std().replace(0, np.nan).fillna(returns.std().mean() or 1.0)
        raw_weights = 1 / np.maximum(vol.to_numpy(), 1e-6)
    elif model == "mean_variance":
        raw_weights = _mean_variance_weights(returns, tickers, view_strengths)
    else:
        posterior = _black_litterman_expected_returns(returns, tickers, view_strengths)
        raw_weights = _mean_variance_weights(
            returns, tickers, view_strengths, expected_returns=posterior
        )

    return _cap_and_scale_weights(
        tickers=tickers,
        raw_weights=raw_weights,
        gross_target=gross_target,
        per_asset_cap=per_asset_cap,
    )


def _build_returns_frame(
    data_window: dict[str, pd.DataFrame],
    tickers: list[str],
    lookback_days: int,
) -> pd.DataFrame:
    series: dict[str, pd.Series] = {}
    minimum_points = max(10, min(lookback_days // 2, 30))

    for ticker in tickers:
        df = data_window.get(ticker)
        if df is None or df.empty or "adj_close" not in df.columns:
            continue
        returns = df["adj_close"].tail(lookback_days + 1).pct_change().dropna()
        if len(returns) >= minimum_points:
            series[ticker] = returns

    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).dropna()


def _mean_variance_weights(
    returns: pd.DataFrame,
    tickers: list[str],
    view_strengths: dict[str, float],
    expected_returns: np.ndarray | None = None,
) -> np.ndarray:
    covariance = _regularized_covariance(returns)
    if expected_returns is None:
        signal_vector = np.array(
            [max(view_strengths[ticker], 1e-6) for ticker in tickers], dtype=float
        )
        signal_vector /= max(signal_vector.sum(), 1e-6)
        expected_returns = signal_vector

    raw = np.linalg.pinv(covariance) @ expected_returns
    raw = np.maximum(raw, 0.0)
    if raw.sum() <= 0:
        return np.ones(len(tickers))
    return raw


def _black_litterman_expected_returns(
    returns: pd.DataFrame,
    tickers: list[str],
    view_strengths: dict[str, float],
) -> np.ndarray:
    covariance = _regularized_covariance(returns)
    n_assets = len(tickers)
    market_weights = np.full(n_assets, 1 / max(n_assets, 1), dtype=float)
    risk_aversion = 2.5
    tau = 0.05
    prior = risk_aversion * covariance @ market_weights

    confidence = np.array([max(view_strengths[ticker], 1e-6) for ticker in tickers], dtype=float)
    confidence /= max(confidence.max(), 1e-6)
    view_scale = np.maximum(np.sqrt(np.diag(covariance)), 1e-6)
    views = prior + confidence * view_scale * 0.25
    omega_diag = np.maximum((1.1 - confidence) * np.diag(tau * covariance), 1e-6)
    omega = np.diag(omega_diag)
    p_matrix = np.eye(n_assets)

    middle = np.linalg.pinv(
        np.linalg.pinv(tau * covariance) + p_matrix.T @ np.linalg.pinv(omega) @ p_matrix
    )
    posterior = middle @ (
        np.linalg.pinv(tau * covariance) @ prior + p_matrix.T @ np.linalg.pinv(omega) @ views
    )
    return np.maximum(posterior, 0.0)


def _regularized_covariance(returns: pd.DataFrame) -> np.ndarray:
    covariance = returns.cov().to_numpy() * 252
    diagonal = np.diag(np.diag(covariance))
    shrunk = 0.8 * covariance + 0.2 * diagonal
    return shrunk + np.eye(len(shrunk)) * 1e-6


def _cap_and_scale_weights(
    tickers: list[str],
    raw_weights: np.ndarray,
    gross_target: float,
    per_asset_cap: float,
) -> dict[str, float]:
    if gross_target <= 0 or len(tickers) == 0:
        return {ticker: 0.0 for ticker in tickers}

    raw = np.maximum(raw_weights.astype(float), 0.0)
    if raw.sum() <= 0:
        raw = np.ones(len(tickers))
    weights = raw / raw.sum() * gross_target
    cap = max(per_asset_cap, 0.0)

    for _ in range(10):
        over_mask = weights > cap + 1e-10
        if not over_mask.any():
            break
        excess = float((weights[over_mask] - cap).sum())
        weights[over_mask] = cap
        under_mask = ~over_mask
        if excess <= 1e-10 or not under_mask.any():
            break
        under_raw = raw[under_mask]
        if under_raw.sum() <= 0:
            weights[under_mask] += excess / under_mask.sum()
        else:
            weights[under_mask] += excess * (under_raw / under_raw.sum())

    return {ticker: float(weight) for ticker, weight in zip(tickers, np.maximum(weights, 0.0))}


async def _apply_sector_limits(
    weights: dict[str, float],
    max_sector_exposure_pct: float,
    warnings: list[str],
) -> dict[str, float]:
    active_tickers = [ticker for ticker, weight in weights.items() if abs(weight) > 1e-8]
    if not active_tickers or max_sector_exposure_pct >= 100:
        return weights

    sector_cap = max(max_sector_exposure_pct / 100, 0.0)
    sector_map = await get_ticker_sectors(active_tickers)
    unresolved = sorted(ticker for ticker, sector in sector_map.items() if not sector)
    if unresolved:
        warnings.append(
            "Sector limits were skipped for unresolved tickers: "
            + ", ".join(unresolved[:5])
            + ("..." if len(unresolved) > 5 else "")
        )

    adjusted = dict(weights)
    exposure_by_sector: defaultdict[str, float] = defaultdict(float)
    for ticker, weight in adjusted.items():
        sector = sector_map.get(ticker)
        if sector:
            exposure_by_sector[sector] += abs(weight)

    for sector, exposure in exposure_by_sector.items():
        if exposure <= sector_cap:
            continue
        scale = sector_cap / exposure
        warnings.append(
            f"Sector limit clipped {sector} exposure from {exposure * 100:.1f}% to {sector_cap * 100:.1f}%."
        )
        for ticker, weight in list(adjusted.items()):
            if sector_map.get(ticker) == sector:
                adjusted[ticker] = weight * scale

    return adjusted


def _apply_gross_cap(weights: dict[str, float], max_gross_exposure_pct: float) -> dict[str, float]:
    gross_cap = max(max_gross_exposure_pct / 100, 0.0)
    gross = sum(abs(weight) for weight in weights.values())
    if gross <= gross_cap or gross <= 1e-8:
        return weights
    scale = gross_cap / gross
    return {ticker: weight * scale for ticker, weight in weights.items()}


def _apply_turnover_limit(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    turnover_limit_pct: float,
) -> tuple[dict[str, float], float]:
    universe = set(current_weights) | set(target_weights)
    deltas = [
        abs(target_weights.get(ticker, 0.0) - current_weights.get(ticker, 0.0))
        for ticker in universe
    ]
    turnover_pct = 0.5 * sum(deltas) * 100
    if turnover_limit_pct <= 0 or turnover_pct <= turnover_limit_pct:
        return target_weights, turnover_pct

    blend = turnover_limit_pct / max(turnover_pct, 1e-8)
    blended = {
        ticker: current_weights.get(ticker, 0.0)
        + (target_weights.get(ticker, 0.0) - current_weights.get(ticker, 0.0)) * blend
        for ticker in universe
    }
    return blended, turnover_limit_pct


def _current_weights(
    portfolio: Portfolio,
    current_prices: dict[str, float],
) -> dict[str, float]:
    equity = max(abs(portfolio.total_equity), 1e-8)
    weights: dict[str, float] = {}
    for ticker, position in portfolio.positions.items():
        price = current_prices.get(ticker, position.current_price)
        if price <= 0:
            continue
        weights[ticker] = (position.shares * price) / equity
    return weights


def _summarize_sector_exposure(weights: dict[str, float]) -> dict[str, float]:
    summary: defaultdict[str, float] = defaultdict(float)
    for _ticker, weight in weights.items():
        if abs(weight) <= 1e-8:
            continue
        summary["Unclassified"] += abs(weight) * 100
    return {sector: round(exposure, 2) for sector, exposure in summary.items()}


def _clean_weights(weights: dict[str, float]) -> dict[str, float]:
    return {ticker: round(weight, 8) for ticker, weight in weights.items() if abs(weight) > 1e-8}
