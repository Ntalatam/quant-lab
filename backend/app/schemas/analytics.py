from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.backtest import PerformanceMetrics, TimeSeriesPoint


class CompareRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backtest_ids": ["bt_sma_001", "bt_momo_002"],
            }
        }
    )

    backtest_ids: list[str] = Field(min_length=2)


class ComparisonBacktest(BaseModel):
    id: str
    strategy_id: str
    tickers: list[str]
    metrics: PerformanceMetrics
    equity_curve: list[TimeSeriesPoint]


class ComparisonResponse(BaseModel):
    backtests: list[ComparisonBacktest]
    correlation_matrix: list[list[float]]


class MonteCarloResult(BaseModel):
    percentiles: dict[str, list[float]]
    n_simulations: int
    n_days: int
    median_final_value: float
    prob_loss: float


class CapacityEstimate(BaseModel):
    adv_threshold_pct: float
    capacity_aum: int | None = None
    label: str


class CapacityTradeStat(BaseModel):
    ticker: str
    side: str
    date: str
    shares: int
    notional: float
    adv: float
    adv_participation_pct: float


class CapacityResponse(BaseModel):
    initial_capital: float | None = None
    n_trades: int | None = None
    max_adv_participation_pct: float | None = None
    avg_adv_participation_pct: float | None = None
    p90_adv_participation_pct: float | None = None
    capacity_estimates: list[CapacityEstimate] = Field(default_factory=list)
    trade_adv_stats: list[CapacityTradeStat] = Field(default_factory=list)
    message: str | None = None


class TransactionCostModel(BaseModel):
    market_impact_model: str
    max_volume_participation_pct: float
    slippage_bps: float
    commission_per_share: float


class TransactionCostSummary(BaseModel):
    total_trades: int
    total_commission: float
    total_spread_cost: float
    total_market_impact_cost: float
    total_timing_cost: float
    total_opportunity_cost: float
    total_borrow_cost: float
    total_locate_fees: float
    total_implementation_shortfall: float
    avg_fill_rate_pct: float
    avg_participation_rate_pct: float
    p90_participation_rate_pct: float
    cost_as_pct_of_initial_capital: float


class TransactionCostTickerBreakdown(BaseModel):
    ticker: str
    trades: int
    total_commission: float
    total_spread_cost: float
    total_market_impact_cost: float
    total_timing_cost: float
    total_opportunity_cost: float
    total_implementation_shortfall: float
    avg_fill_rate_pct: float
    avg_participation_rate_pct: float


class TransactionCostTrade(BaseModel):
    id: str
    ticker: str
    side: str
    position_direction: str
    date: str
    shares: int
    requested_shares: int
    unfilled_shares: int
    commission: float
    spread_cost: float
    market_impact_cost: float
    timing_cost: float
    opportunity_cost: float
    implementation_shortfall: float
    fill_rate_pct: float
    participation_rate_pct: float
    risk_event: str | None = None


class TransactionCostAnalysisResponse(BaseModel):
    model: TransactionCostModel
    summary: TransactionCostSummary
    ticker_breakdown: list[TransactionCostTickerBreakdown] = Field(default_factory=list)
    top_cost_trades: list[TransactionCostTrade] = Field(default_factory=list)
    message: str | None = None


class RegimeTimelinePoint(BaseModel):
    date: str
    regime: str
    return_: float = Field(alias="return")

    model_config = ConfigDict(populate_by_name=True)


class RegimeStat(BaseModel):
    regime: str
    color: str
    days: int
    pct_of_period: float
    ann_return_pct: float
    ann_volatility_pct: float
    sharpe: float


class RegimeAnalysisResponse(BaseModel):
    timeline: list[RegimeTimelinePoint]
    regime_stats: list[RegimeStat]
    description: str


class FactorLoading(BaseModel):
    name: str
    beta: float
    t_stat: float
    p_value: float
    significant: bool


class FactorExposureResponse(BaseModel):
    alpha_annualized: float
    r_squared: float
    n_obs: int
    factors: list[FactorLoading]


class PortfolioBlendRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backtest_ids": ["bt_sma_001", "bt_momo_002"],
                "weights": [0.5, 0.5],
                "optimize": "equal",
            }
        }
    )

    backtest_ids: list[str] = Field(min_length=2)
    weights: list[float] = Field(default_factory=list)
    optimize: Literal["custom", "equal", "max_sharpe", "min_dd"] = "custom"


class CorrelationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tickers": ["AAPL", "MSFT", "GOOGL", "SPY"],
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
                "rolling_window": 63,
            }
        }
    )

    tickers: list[str] = Field(min_length=2, description="Tickers to analyse")
    start_date: str = Field(description="ISO start date")
    end_date: str = Field(description="ISO end date")
    rolling_window: int = Field(
        default=63, ge=10, le=504, description="Rolling window in trading days"
    )
    max_pairs: int = Field(default=10, ge=1, le=50, description="Max pairs for auto-discovery")


class RollingCorrelationSeries(BaseModel):
    pair: str
    ticker_a: str
    ticker_b: str
    series: list[TimeSeriesPoint]


class PairTestResult(BaseModel):
    ticker_a: str
    ticker_b: str
    adf_statistic: float
    adf_pvalue: float
    cointegrated: bool
    beta: float
    half_life_days: float | None = None
    current_zscore: float | None = None
    spread_std: float


class SpreadAnalysis(BaseModel):
    spread_series: list[TimeSeriesPoint]
    zscore_series: list[TimeSeriesPoint]
    half_life_days: float | None = None
    current_zscore: float | None = None
    spread_mean: float
    spread_std: float


class CorrelationResponse(BaseModel):
    tickers: list[str]
    static_matrix: list[list[float]]
    rolling_correlations: list[RollingCorrelationSeries]
    discovered_pairs: list[PairTestResult]


class SpreadRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker_a": "AAPL",
                "ticker_b": "MSFT",
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
                "lookback": 63,
            }
        }
    )

    ticker_a: str
    ticker_b: str
    start_date: str
    end_date: str
    lookback: int = Field(default=63, ge=10, le=504)


class SpreadResponse(BaseModel):
    ticker_a: str
    ticker_b: str
    spread_series: list[TimeSeriesPoint]
    zscore_series: list[TimeSeriesPoint]
    half_life_days: float | None = None
    current_zscore: float | None = None
    spread_mean: float
    spread_std: float
    cointegration: PairTestResult


class PortfolioContribution(BaseModel):
    id: str
    strategy_id: str
    tickers: list[str]
    weight: float
    asset_return_pct: float
    contribution_pct: float


class PortfolioBlendResponse(BaseModel):
    weights: list[float]
    optimize: str
    equity_curve: list[TimeSeriesPoint]
    metrics: PerformanceMetrics | dict[str, float | int | str | bool]
    asset_contributions: list[PortfolioContribution]
