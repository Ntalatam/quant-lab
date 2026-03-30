from pydantic import BaseModel, Field


class BacktestConfig(BaseModel):
    strategy_id: str
    params: dict = {}
    tickers: list[str] = Field(min_length=1)
    benchmark: str = "SPY"
    start_date: str
    end_date: str
    initial_capital: float = 100_000
    slippage_bps: float = 5.0
    commission_per_share: float = 0.005
    position_sizing: str = "equal_weight"
    max_position_pct: float = 25.0
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
