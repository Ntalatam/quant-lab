from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ParamValue = int | float | str | bool


class BacktestConfig(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "strategy_id": "sma_crossover",
                "params": {
                    "short_window": 20,
                    "long_window": 60,
                    "position_weight": 0.95,
                },
                "tickers": ["AAPL", "MSFT"],
                "benchmark": "SPY",
                "start_date": "2019-01-01",
                "end_date": "2024-01-01",
                "initial_capital": 100000,
                "slippage_bps": 5,
                "commission_per_share": 0.005,
                "market_impact_model": "almgren_chriss",
                "max_volume_participation_pct": 5,
                "position_sizing": "equal_weight",
                "portfolio_construction_model": "equal_weight",
                "portfolio_lookback_days": 63,
                "max_position_pct": 25,
                "max_gross_exposure_pct": 150,
                "turnover_limit_pct": 100,
                "max_sector_exposure_pct": 100,
                "allow_short_selling": False,
                "max_short_position_pct": 25,
                "short_margin_requirement_pct": 50,
                "short_borrow_rate_bps": 200,
                "short_locate_fee_bps": 10,
                "short_squeeze_threshold_pct": 15,
                "rebalance_frequency": "daily",
            }
        }
    )

    strategy_id: str
    params: dict[str, ParamValue] = Field(default_factory=dict)
    tickers: list[str] = Field(min_length=1)
    benchmark: str = "SPY"
    start_date: str
    end_date: str
    initial_capital: float = 100_000
    slippage_bps: float = 5.0
    commission_per_share: float = 0.005
    market_impact_model: Literal["constant", "almgren_chriss"] = "almgren_chriss"
    max_volume_participation_pct: float = 5.0
    position_sizing: str = "equal_weight"
    portfolio_construction_model: str = "equal_weight"
    portfolio_lookback_days: int = 63
    max_position_pct: float = 25.0
    max_gross_exposure_pct: float = 150.0
    turnover_limit_pct: float = 100.0
    max_sector_exposure_pct: float = 100.0
    allow_short_selling: bool = False
    max_short_position_pct: float = 25.0
    short_margin_requirement_pct: float = 50.0
    short_borrow_rate_bps: float = 200.0
    short_locate_fee_bps: float = 10.0
    short_squeeze_threshold_pct: float = 15.0
    rebalance_frequency: Literal["daily", "weekly", "monthly"] = "daily"


class TimeSeriesPoint(BaseModel):
    date: str
    value: float


class MonthlyReturn(BaseModel):
    year: int
    month: int
    return_pct: float


class PerformanceMetrics(BaseModel):
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    cagr_pct: float = 0.0
    annualized_volatility_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    current_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    var_95_pct: float = 0.0
    cvar_95_pct: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    total_trades: int = 0
    win_rate_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    avg_holding_period_days: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    avg_exposure_pct: float = 0.0
    max_exposure_pct: float = 0.0
    avg_net_exposure_pct: float = 0.0
    max_net_exposure_pct: float = 0.0
    avg_short_exposure_pct: float = 0.0
    max_short_exposure_pct: float = 0.0
    avg_turnover_pct: float = 0.0
    max_turnover_pct: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    correlation: float = 0.0
    tracking_error_pct: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    total_spread_cost: float = 0.0
    total_market_impact_cost: float = 0.0
    total_timing_cost: float = 0.0
    total_opportunity_cost: float = 0.0
    total_implementation_shortfall: float = 0.0
    avg_fill_rate_pct: float = 0.0
    avg_participation_rate_pct: float = 0.0
    total_borrow_cost: float = 0.0
    total_locate_fees: float = 0.0
    total_cost: float = 0.0
    cost_drag_bps: float = 0.0
    cost_drag_pct: float = 0.0


class TradeResponse(BaseModel):
    id: str
    ticker: str
    side: Literal["BUY", "SELL"]
    position_direction: Literal["LONG", "SHORT"]
    entry_date: str
    entry_price: float
    exit_date: str | None = None
    exit_price: float | None = None
    shares: int
    requested_shares: int = 0
    unfilled_shares: int = 0
    pnl: float | None = None
    pnl_pct: float | None = None
    commission: float = 0.0
    slippage: float = 0.0
    spread_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    participation_rate_pct: float = 0.0
    implementation_shortfall: float = 0.0
    borrow_cost: float = 0.0
    locate_fee: float = 0.0
    risk_event: str | None = None


class BacktestResultResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "bt_sma_001",
                "config": BacktestConfig.model_config["json_schema_extra"]["example"],
                "created_at": "2026-04-03T12:00:00Z",
                "notes": "",
                "equity_curve": [{"date": "2024-01-02", "value": 100000.0}],
                "clean_equity_curve": [{"date": "2024-01-02", "value": 100050.0}],
                "benchmark_curve": [{"date": "2024-01-02", "value": 100000.0}],
                "drawdown_series": [{"date": "2024-01-02", "value": 0.0}],
                "rolling_sharpe": [{"date": "2024-06-01", "value": 1.42}],
                "rolling_volatility": [{"date": "2024-06-01", "value": 14.2}],
                "metrics": {"total_return_pct": 18.4, "sharpe_ratio": 1.42},
                "benchmark_metrics": {"total_return_pct": 11.1, "sharpe_ratio": 0.92},
                "trades": [],
                "monthly_returns": [{"year": 2024, "month": 1, "return_pct": 1.2}],
            }
        }
    )

    id: str
    config: BacktestConfig
    created_at: str | None = None
    notes: str = ""
    equity_curve: list[TimeSeriesPoint]
    clean_equity_curve: list[TimeSeriesPoint] = Field(default_factory=list)
    benchmark_curve: list[TimeSeriesPoint]
    drawdown_series: list[TimeSeriesPoint]
    rolling_sharpe: list[TimeSeriesPoint]
    rolling_volatility: list[TimeSeriesPoint]
    metrics: PerformanceMetrics
    benchmark_metrics: PerformanceMetrics
    trades: list[TradeResponse]
    monthly_returns: list[MonthlyReturn]


class BacktestSummaryResponse(BaseModel):
    id: str
    strategy_name: str
    tickers: list[str]
    start_date: str
    end_date: str
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    created_at: str | None = None


class BacktestListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "bt_sma_001",
                        "strategy_name": "sma_crossover",
                        "tickers": ["AAPL", "MSFT"],
                        "start_date": "2019-01-01",
                        "end_date": "2024-01-01",
                        "total_return_pct": 18.4,
                        "sharpe_ratio": 1.42,
                        "max_drawdown_pct": -9.6,
                        "created_at": "2026-04-03T12:00:00Z",
                    }
                ],
                "total": 1,
            }
        }
    )

    items: list[BacktestSummaryResponse]
    total: int


class NotesUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notes": "Strong performance during trending regimes; review cost drag before deploying.",
            }
        }
    )

    notes: str = Field(default="", max_length=2000)


class NotesUpdateResponse(BaseModel):
    id: str
    notes: str


class BacktestSweepConfig(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "base_config": BacktestConfig.model_config["json_schema_extra"]["example"],
                "sweep_param": "short_window",
                "sweep_values": [10, 20, 30],
            }
        }
    )

    base_config: BacktestConfig
    sweep_param: str
    sweep_values: list[float | int | str]


class SweepResultItem(BaseModel):
    param_value: float | int | str
    sharpe_ratio: float | None = None
    total_return_pct: float | None = None
    max_drawdown_pct: float | None = None
    cagr_pct: float | None = None
    error: str | None = None


class SweepResponse(BaseModel):
    sweep_param: str
    results: list[SweepResultItem]


class BacktestSweep2DConfig(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "base_config": BacktestConfig.model_config["json_schema_extra"]["example"],
                "param_x": "short_window",
                "values_x": [10, 20, 30],
                "param_y": "long_window",
                "values_y": [40, 60, 80],
                "metric": "sharpe_ratio",
            }
        }
    )

    base_config: BacktestConfig
    param_x: str
    values_x: list[float | int]
    param_y: str
    values_y: list[float | int]
    metric: str = "sharpe_ratio"


class Sweep2DCell(BaseModel):
    x: float | int
    y: float | int
    value: float | None = None
    total_return_pct: float | None = None
    max_drawdown_pct: float | None = None
    error: str | None = None


class Sweep2DResponse(BaseModel):
    param_x: str
    param_y: str
    metric: str
    values_x: list[float | int]
    values_y: list[float | int]
    cells: list[list[Sweep2DCell]]


class WalkForwardRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config": BacktestConfig.model_config["json_schema_extra"]["example"],
                "n_folds": 5,
                "train_pct": 0.7,
            }
        }
    )

    config: BacktestConfig
    n_folds: int = Field(default=5, ge=2, le=10)
    train_pct: float = Field(default=0.7, ge=0.5, le=0.9)


class WalkForwardFold(BaseModel):
    fold: int
    is_start: str
    is_end: str
    oos_start: str
    oos_end: str
    is_sharpe: float | None = None
    is_return: float | None = None
    oos_sharpe: float | None = None
    oos_return: float | None = None
    oos_max_dd: float | None = None
    ok: bool


class WalkForwardResponse(BaseModel):
    n_folds: int
    train_pct: float
    folds: list[WalkForwardFold]
    oos_equity_curve: list[TimeSeriesPoint]
    oos_metrics: PerformanceMetrics | dict[str, float | int | str | bool] = Field(
        default_factory=dict
    )
    sharpe_efficiency: float | None = None


class BayesOptParamSpec(BaseModel):
    name: str
    type: Literal["int", "float"]
    low: float
    high: float
    step: float | None = None


class BayesOptConfig(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "base_config": BacktestConfig.model_config["json_schema_extra"]["example"],
                "param_specs": [
                    {
                        "name": "short_window",
                        "type": "int",
                        "low": 5,
                        "high": 50,
                        "step": 1,
                    }
                ],
                "metric": "sharpe_ratio",
                "n_trials": 20,
                "maximize": True,
            }
        }
    )

    base_config: BacktestConfig
    param_specs: list[BayesOptParamSpec]
    metric: str = "sharpe_ratio"
    n_trials: int = 30
    maximize: bool = True


class BayesOptTrial(BaseModel):
    trial: int
    params: dict[str, ParamValue]
    value: float


class BayesOptResponse(BaseModel):
    best_params: dict[str, ParamValue]
    best_value: float
    metric: str
    n_trials: int
    trials: list[BayesOptTrial]
    param_specs: list[BayesOptParamSpec]
