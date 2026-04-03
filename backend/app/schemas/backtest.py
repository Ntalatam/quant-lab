from pydantic import BaseModel, Field


class BacktestConfig(BaseModel):
    strategy_id: str
    params: dict = Field(default_factory=dict)
    tickers: list[str] = Field(min_length=1)
    benchmark: str = "SPY"
    start_date: str
    end_date: str
    initial_capital: float = 100_000
    slippage_bps: float = 5.0
    commission_per_share: float = 0.005
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
    rebalance_frequency: str = "daily"


class BacktestSweepConfig(BaseModel):
    base_config: BacktestConfig
    sweep_param: str
    sweep_values: list[float | int | str]


class BacktestSweep2DConfig(BaseModel):
    base_config: BacktestConfig
    param_x: str
    values_x: list[float | int]
    param_y: str
    values_y: list[float | int]
    metric: str = "sharpe_ratio"  # metric to display in the heatmap


class BayesOptParamSpec(BaseModel):
    name: str
    type: str          # "int" or "float"
    low: float
    high: float
    step: float | None = None  # only for int params


class BayesOptConfig(BaseModel):
    base_config: BacktestConfig
    param_specs: list[BayesOptParamSpec]
    metric: str = "sharpe_ratio"  # objective to maximize
    n_trials: int = 30
    maximize: bool = True
