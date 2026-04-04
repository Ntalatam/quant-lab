"""
POST /api/options/price         — Black-Scholes pricing with full Greeks
POST /api/options/implied-vol   — Implied volatility solver
POST /api/options/chain         — Synthetic options chain
POST /api/options/vol-surface   — Volatility surface with skew
POST /api/options/pnl-scenario  — P&L scenario analysis
"""

from fastapi import APIRouter

from app.schemas.common import ErrorResponse
from app.schemas.options import (
    ChainRequest,
    ChainResponse,
    ImpliedVolRequest,
    ImpliedVolResponse,
    OptionPriceRequest,
    OptionPriceResponse,
    PnlScenarioRequest,
    PnlScenarioResponse,
    VolSurfaceRequest,
    VolSurfaceResponse,
)
from app.services.options import (
    black_scholes,
    compute_pnl_grid,
    generate_options_chain,
    generate_vol_surface,
    implied_volatility,
)

router = APIRouter(prefix="/options", tags=["options"])


@router.post(
    "/price",
    response_model=OptionPriceResponse,
    summary="Price an option with full Greeks",
    description=(
        "Black-Scholes-Merton pricing for a European option. Returns price, "
        "delta, gamma, theta (per day), vega (per 1% vol), rho (per 1% rate), "
        "intrinsic value, and time value."
    ),
)
async def price_option(payload: OptionPriceRequest):
    T = payload.days_to_expiry / 365.0
    result = black_scholes(
        payload.spot, payload.strike, T,
        payload.risk_free_rate, payload.volatility, payload.option_type,
    )
    moneyness = payload.spot / payload.strike
    if moneyness > 1.02:
        label = "ITM" if payload.option_type == "call" else "OTM"
    elif moneyness < 0.98:
        label = "OTM" if payload.option_type == "call" else "ITM"
    else:
        label = "ATM"

    return {
        "price": result.price,
        "delta": result.delta,
        "gamma": result.gamma,
        "theta": result.theta,
        "vega": result.vega,
        "rho": result.rho,
        "intrinsic": result.intrinsic,
        "time_value": result.time_value,
        "option_type": payload.option_type,
        "moneyness": round(moneyness, 4),
        "moneyness_label": label,
    }


@router.post(
    "/implied-vol",
    response_model=ImpliedVolResponse,
    summary="Solve for implied volatility",
    description=(
        "Given an observed market price, solves for the implied volatility "
        "using Brent's root-finding method."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "No valid IV solution found."},
    },
)
async def solve_implied_vol(payload: ImpliedVolRequest):
    T = payload.days_to_expiry / 365.0
    iv = implied_volatility(
        payload.market_price, payload.spot, payload.strike,
        T, payload.risk_free_rate, payload.option_type,
    )
    theo = None
    if iv is not None:
        theo = black_scholes(
            payload.spot, payload.strike, T,
            payload.risk_free_rate, iv, payload.option_type,
        ).price

    return {
        "implied_volatility": iv,
        "implied_volatility_pct": round(iv * 100, 2) if iv else None,
        "market_price": payload.market_price,
        "theoretical_price": theo,
        "message": (
            f"IV = {iv * 100:.2f}%" if iv else "Could not solve for implied volatility"
        ),
    }


@router.post(
    "/chain",
    response_model=ChainResponse,
    summary="Generate synthetic options chain",
    description=(
        "Produces a full options chain with calls and puts across multiple "
        "expiries and strikes, using Black-Scholes pricing."
    ),
)
async def options_chain(payload: ChainRequest):
    chain = generate_options_chain(
        payload.spot,
        payload.risk_free_rate,
        payload.volatility,
        payload.days_to_expiry,
        payload.strike_range_pct,
        payload.n_strikes,
    )
    return {"spot": payload.spot, "chain": chain}


@router.post(
    "/vol-surface",
    response_model=VolSurfaceResponse,
    summary="Generate implied volatility surface",
    description=(
        "Builds a synthetic IV surface with realistic skew (put skew + smile). "
        "Short-dated options exhibit steeper skew. Useful for understanding "
        "volatility term structure and moneyness effects."
    ),
)
async def vol_surface(payload: VolSurfaceRequest):
    result = generate_vol_surface(
        payload.spot,
        payload.risk_free_rate,
        payload.base_volatility,
        payload.days_to_expiry,
        payload.n_strikes,
        payload.strike_range_pct,
    )
    return result


@router.post(
    "/pnl-scenario",
    response_model=PnlScenarioResponse,
    summary="Option P&L scenario analysis",
    description=(
        "Computes option P&L across a grid of spot prices at multiple "
        "time-to-expiry snapshots. Shows how time decay and spot movement "
        "interact to produce the P&L profile."
    ),
)
async def pnl_scenario(payload: PnlScenarioRequest):
    T = payload.days_to_expiry / 365.0
    result = compute_pnl_grid(
        payload.spot, payload.strike, T,
        payload.risk_free_rate, payload.volatility,
        payload.option_type, payload.position,
        payload.entry_price, payload.price_range_pct,
    )
    return result
