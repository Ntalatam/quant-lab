"""
Execution simulator.

Models realistic order execution with slippage, commissions, and volume constraints.
Without these costs, strategies show inflated returns.
"""

from dataclasses import dataclass


@dataclass
class FillResult:
    filled: bool
    fill_price: float
    shares_filled: int
    requested_shares: int
    unfilled_shares: int
    commission: float
    slippage_cost: float
    spread_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    implementation_shortfall: float = 0.0
    participation_rate_pct: float = 0.0
    estimated_spread_bps: float = 0.0
    estimated_impact_bps: float = 0.0
    reason: str = ""


def simulate_fill(
    side: str,
    shares: int,
    bar_open: float,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    bar_volume: int,
    slippage_bps: float,
    commission_per_share: float,
    market_impact_model: str = "constant",
    max_volume_participation: float = 0.05,
) -> FillResult:
    """
    Simulate order execution for a single bar.

    Fill price = open price +/- slippage, clamped to bar's high/low range.
    Volume constraint: cannot fill more than max_volume_participation * bar_volume.
    """
    requested_shares = max(int(shares), 0)
    max_shares = int(bar_volume * max_volume_participation)
    if max_shares <= 0:
        return FillResult(
            False,
            0,
            0,
            requested_shares=requested_shares,
            unfilled_shares=requested_shares,
            commission=0,
            slippage_cost=0,
            reason="Insufficient volume",
        )

    actual_shares = min(requested_shares, max_shares)
    unfilled_shares = max(requested_shares - actual_shares, 0)
    participation_rate_pct = (
        (actual_shares / max(bar_volume, 1)) * 100 if actual_shares > 0 else 0.0
    )

    if market_impact_model == "almgren_chriss":
        modeled = _almgren_chriss_costs(
            side=side,
            requested_shares=requested_shares,
            actual_shares=actual_shares,
            bar_open=bar_open,
            bar_high=bar_high,
            bar_low=bar_low,
            bar_close=bar_close,
            bar_volume=bar_volume,
            slippage_bps=slippage_bps,
        )
        fill_price = modeled["fill_price"]
        spread_cost = modeled["spread_cost"]
        market_impact_cost = modeled["market_impact_cost"]
        timing_cost = modeled["timing_cost"]
        opportunity_cost = modeled["opportunity_cost"]
        estimated_spread_bps = modeled["estimated_spread_bps"]
        estimated_impact_bps = modeled["estimated_impact_bps"]
    else:
        slippage_mult = slippage_bps / 10_000
        if side == "BUY":
            fill_price = bar_open * (1 + slippage_mult)
            fill_price = min(fill_price, bar_high)
        else:
            fill_price = bar_open * (1 - slippage_mult)
            fill_price = max(fill_price, bar_low)
        spread_cost = abs(fill_price - bar_open) * actual_shares
        market_impact_cost = 0.0
        timing_cost = 0.0
        opportunity_cost = 0.0
        estimated_spread_bps = slippage_bps
        estimated_impact_bps = 0.0

    commission = actual_shares * commission_per_share
    slippage_cost = spread_cost + market_impact_cost
    implementation_shortfall = (
        commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
    )

    return FillResult(
        filled=True,
        fill_price=fill_price,
        shares_filled=actual_shares,
        requested_shares=requested_shares,
        unfilled_shares=unfilled_shares,
        commission=commission,
        slippage_cost=slippage_cost,
        spread_cost=spread_cost,
        market_impact_cost=market_impact_cost,
        timing_cost=timing_cost,
        opportunity_cost=opportunity_cost,
        implementation_shortfall=implementation_shortfall,
        participation_rate_pct=participation_rate_pct,
        estimated_spread_bps=estimated_spread_bps,
        estimated_impact_bps=estimated_impact_bps,
    )


def _almgren_chriss_costs(
    side: str,
    requested_shares: int,
    actual_shares: int,
    bar_open: float,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    bar_volume: int,
    slippage_bps: float,
) -> dict[str, float]:
    sign = 1 if side == "BUY" else -1
    actual_participation = actual_shares / max(bar_volume, 1)
    intrabar_vol = max(
        abs(bar_high - bar_low) / max(bar_open, 1e-8),
        abs(bar_close - bar_open) / max(bar_open, 1e-8),
        0.0005,
    )

    spread_bps = max(
        slippage_bps * 0.4,
        1.0 + 150 * intrabar_vol + 20 * (actual_participation**0.5),
    )
    temporary_impact_bps = max(
        slippage_bps * 0.6,
        350 * intrabar_vol * (actual_participation**0.5) + 45 * actual_participation,
    )
    permanent_impact_bps = 120 * intrabar_vol * actual_participation
    impact_bps = temporary_impact_bps + permanent_impact_bps

    modeled_spread_cost = bar_open * (spread_bps / 10_000) * actual_shares
    modeled_impact_cost = bar_open * (impact_bps / 10_000) * actual_shares
    modeled_total_cost = modeled_spread_cost + modeled_impact_cost
    modeled_fill_price = bar_open + sign * (modeled_total_cost / max(actual_shares, 1))

    if side == "BUY":
        fill_price = min(modeled_fill_price, bar_high)
    else:
        fill_price = max(modeled_fill_price, bar_low)

    realized_total_cost = abs(fill_price - bar_open) * actual_shares
    scale = realized_total_cost / max(modeled_total_cost, 1e-8) if modeled_total_cost > 0 else 0.0
    spread_cost = modeled_spread_cost * scale
    market_impact_cost = modeled_impact_cost * scale

    adverse_move_per_share = max(sign * (bar_close - bar_open), 0.0)
    timing_cost = adverse_move_per_share * actual_shares
    opportunity_cost = adverse_move_per_share * max(requested_shares - actual_shares, 0)

    return {
        "fill_price": fill_price,
        "spread_cost": spread_cost,
        "market_impact_cost": market_impact_cost,
        "timing_cost": timing_cost,
        "opportunity_cost": opportunity_cost,
        "estimated_spread_bps": spread_bps,
        "estimated_impact_bps": impact_bps,
    }
