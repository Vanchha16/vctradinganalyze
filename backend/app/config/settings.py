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

    # Phase 8E (docs/59 §9, ADR-119) - public self-registration is closed by
    # default. Accounts are admin-provisioned only (AdminUserService) or
    # created once via backend/scripts/create_admin.py's bootstrap flow.
    allow_public_registration: bool = False

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

    news_providers: list[str] = ["mock"]
    news_ingestion_interval_seconds: int = 300
    news_lookback_hours: int = 24

    news_api_key: str = ""
    news_api_base_url: str = "https://newsapi.org"
    news_api_timeout_seconds: float = 10.0

    economic_calendar_providers: list[str] = ["mock"]
    economic_calendar_ingestion_interval_seconds: int = 900
    economic_calendar_lookback_days: int = 7
    economic_calendar_lookahead_days: int = 30

    economic_api_key: str = ""
    economic_api_base_url: str = "https://finnhub.io"
    economic_api_timeout_seconds: float = 10.0

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 15.0

    ai_orchestrator_providers: list[str] = ["openai"]
    ai_retry_max_attempts: int = 2
    ai_retry_backoff_seconds: float = 1.0

    signal_ttl_hours: int = 24

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_base_url: str = "https://api.telegram.org"
    telegram_timeout_seconds: float = 30.0
    telegram_providers: list[str] = ["mock"]
    telegram_poll_interval_seconds: int = 5

    chat_max_history_messages: int = 20

    # Phase 9 (ADR-127) - the first inbound (per-user) throttle in this
    # project, scoped to the two endpoints that spend real LLM tokens per
    # call. Conservative starting points, not empirically calibrated - see
    # ADR-127's Future Review.
    ai_analysis_quota_limit: int = 10
    ai_analysis_quota_window_seconds: int = 3600
    ai_chat_quota_limit: int = 30
    ai_chat_quota_window_seconds: int = 3600

    # Phase 9A (ADR-132) - trusted immediate-peer address(es) for resolving
    # the real client IP behind a reverse proxy, passed verbatim to
    # uvicorn's `--forwarded-allow-ips` (comma-separated, or "*"). Defaults
    # to loopback: correct for local dev (no proxy - the flag has no
    # effect) and for production, where Nginx runs on the same host
    # (docs/27) and connects to uvicorn via 127.0.0.1.
    trusted_proxy_ips: str = "127.0.0.1"

    # Phase 9A (ADR-132) - per-IP rate limits for the public, unauthenticated
    # route modules (docs/60 §4.2). Two tiers: "engine" routes
    # (technical/SMC/regime/confidence/strategy/risk) run a full pass over
    # ~500 candles per request; "data" routes (assets/candles/news/calendar)
    # are cheap reads. Sized generously above measured real page-load
    # traffic (docs/60 §4.2) - hand-picked starting points, not calibrated,
    # same caveat as ADR-127's quotas.
    public_rate_limit_engine_limit: int = 20
    public_rate_limit_data_limit: int = 100
    public_rate_limit_window_seconds: int = 60

    # Phase 9B (ADR-133, docs/23 §17) - failed-login lockout. docs/23 §17
    # names the requirement ("Temporary Lock") with no threshold/duration;
    # these are hand-picked starting points, not calibrated, same caveat
    # as ADR-127's quotas and ADR-132's rate limits. Auto-expiry (not an
    # admin-unlock endpoint) is the recovery path - see ADR-133.
    login_lockout_threshold: int = 5
    login_lockout_duration_minutes: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
