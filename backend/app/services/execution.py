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
    commission: float
    slippage_cost: float
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
    max_volume_participation: float = 0.05,
) -> FillResult:
    """
    Simulate order execution for a single bar.

    Fill price = open price +/- slippage, clamped to bar's high/low range.
    Volume constraint: cannot fill more than max_volume_participation * bar_volume.
    """
    max_shares = int(bar_volume * max_volume_participation)
    if max_shares <= 0:
        return FillResult(False, 0, 0, 0, 0, "Insufficient volume")

    actual_shares = min(shares, max_shares)

    slippage_mult = slippage_bps / 10_000
    if side == "BUY":
        fill_price = bar_open * (1 + slippage_mult)
        fill_price = min(fill_price, bar_high)
    else:
        fill_price = bar_open * (1 - slippage_mult)
        fill_price = max(fill_price, bar_low)

    commission = actual_shares * commission_per_share
    slippage_cost = abs(fill_price - bar_open) * actual_shares

    return FillResult(
        filled=True,
        fill_price=fill_price,
        shares_filled=actual_shares,
        commission=commission,
        slippage_cost=slippage_cost,
    )
