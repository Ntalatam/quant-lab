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
    AUTH_SECRET_KEY: str = "change-me-in-production"
    AUTH_ACCESS_TOKEN_TTL_MINUTES: int = 15
    AUTH_REFRESH_TOKEN_TTL_DAYS: int = 30
    AUTH_REFRESH_COOKIE_NAME: str = "quantlab_refresh_token"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"
    JOB_WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    JOB_MAX_ATTEMPTS: int = 1
    MARKET_DATA_PROVIDER: str = "yfinance"
    ECONOMIC_DATA_PROVIDER: str = "fred"
    EARNINGS_DATA_PROVIDER: str = "yfinance"
    NEWS_SENTIMENT_PROVIDER: str = "yfinance"
    ASSET_METADATA_PROVIDER: str = "yfinance"
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    model_config = {"env_file": ".env"}

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
