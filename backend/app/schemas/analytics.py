from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    backtest_ids: list[str] = Field(min_length=2)


class MonteCarloRequest(BaseModel):
    n_simulations: int = 1000
    n_days: int = 252
