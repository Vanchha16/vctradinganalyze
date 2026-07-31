from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClaudeTradingAI"
    app_env: str = "development"
    app_debug: bool = False
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://trading_user:change-me@localhost:5432/trading_app"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_this_secret"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30

    market_data_providers: list[str] = ["mock"]
    market_data_retry_max_attempts: int = 3
    market_data_retry_backoff_seconds: float = 1.0
    market_data_default_rate_limit_per_minute: float = 60.0
    market_data_rate_limits_per_minute: dict[str, float] = {"mock": 6000.0, "twelve_data": 8.0}
    market_data_default_rate_limit_per_day: float | None = None
    market_data_rate_limits_per_day: dict[str, float] = {"twelve_data": 800.0}

    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    twelve_data_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
