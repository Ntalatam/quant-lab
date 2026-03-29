from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://quantlab:quantlab@localhost:5432/quantlab"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    FRED_API_KEY: str = ""
    DEFAULT_SLIPPAGE_BPS: float = 5.0
    DEFAULT_COMMISSION_PER_SHARE: float = 0.005
    DEFAULT_INITIAL_CAPITAL: float = 100_000.0
    MAX_BACKTEST_YEARS: int = 20

    model_config = {"env_file": ".env"}


settings = Settings()
