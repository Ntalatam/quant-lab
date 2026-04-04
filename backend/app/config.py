from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "quantlab-backend"
    APP_ENV: str = "development"  # development | staging | production
    DATABASE_URL: str = "sqlite+aiosqlite:///./quantlab.db"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    FRED_API_KEY: str = ""
    DEFAULT_SLIPPAGE_BPS: float = 5.0
    DEFAULT_COMMISSION_PER_SHARE: float = 0.005
    DEFAULT_INITIAL_CAPITAL: float = 100_000.0
    MAX_BACKTEST_YEARS: int = 20
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    SLOW_REQUEST_THRESHOLD_MS: float = 750.0

    model_config = {"env_file": ".env"}

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
