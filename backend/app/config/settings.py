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
    # Phase 9H (ADR-140): the Beat interval used to just be each timeframe's
    # own duration, so M1 collected every 60s - 1,440 runs/day/asset alone,
    # blowing through Twelve Data's 800/day cap in ~4 hours and going dark
    # for the rest of the day (production incident, 2026-08-07). This floor
    # is applied as `max(timeframe_duration, floor)` when building the Beat
    # schedule - lossless (each fetch backfills via `outputsize=5000` +
    # upsert, docs/40 §2), the only cost is added latency on how fresh the
    # newest candle can be.
    market_data_min_collection_interval_seconds: float = 300.0

    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    twelve_data_timeout_seconds: float = 10.0

    news_providers: list[str] = ["mock"]
    # Cleanup (2026-08-07): was 300s (288 runs/day) - NewsAPI's free
    # Developer plan caps at 100 requests/day, so the old default
    # exhausted it in ~8 hours, every day, before counting health
    # checks or admin-triggered refreshes. 1800s = 48 runs/day, well
    # inside the cap with headroom. No provider-side quota enforcement
    # exists for news (unlike market data's `RateLimitedProvider`,
    # ADR-025) - a misconfigured interval still silently burns vendor
    # budget with nothing stopping it (BACKLOG.md §16).
    news_ingestion_interval_seconds: int = 1800
    # Cleanup (2026-08-07): was 24h - NewsAPI's free Developer plan
    # delays article availability by roughly 24h, so a 24h lookback
    # queried exactly the window the free tier had not published yet,
    # guaranteeing zero results on every run. 72h covers that
    # delay with margin. Safe to widen: `dedup_detector` skips articles
    # already seen (URL/title match), so re-scanning a larger overlap
    # is still idempotent, not a double-count risk.
    news_lookback_hours: int = 72

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

    # Phase 9E (ADR-137) - separate TTL for an already-`TRIGGERED` (live)
    # signal, distinct from `signal_ttl_hours` (pending-order TTL). A live
    # trade left open indefinitely would never close and would permanently
    # block ADR-125's dedup gate for that asset. Hand-picked starting point
    # (7 days) - not empirically calibrated, same caveat as every other
    # threshold constant in this project.
    signal_triggered_ttl_hours: int = 168

    # Phase 9E (ADR-137) - hourly signal-generation cadence, moved out of a
    # module constant (`workers/signal_tasks.py`) so the operator can retune
    # it via `.env` + restart without a code change/deploy. Default
    # unchanged from the prior hardcoded value.
    signal_generation_interval_seconds: float = 3600.0

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

    # Phase 9D (ADR-136) - GET /metrics access control. Empty by default:
    # an unconfigured deployment gets a 404 (not 403, not an empty 200),
    # so the endpoint does not advertise its own existence until someone
    # deliberately opts in. A static bearer token, not `require_admin` -
    # scrapers cannot hold a user session, and this must keep responding
    # when the database is unhealthy, which is exactly when metrics
    # matter most. The real production boundary is Nginx denying
    # external access to the path; this token is defence in depth, not
    # a substitute.
    metrics_auth_token: str = ""

    # Phase 11 (EA Bot, .claude/specs/phase-11-ea-bot-exness-mt5-execution.md
    # §0.6/§0.9) - hard kill switch for real order placement. Default
    # `False` in every environment including production; only the operator
    # may flip this to `True`, after personally reviewing §12's dry-run
    # output, in a fresh action - never as part of a deploy/build step.
    execution_enabled: bool = False
    # Deliberately singular, unlike `market_data_providers` (a failover
    # chain is safe for read-only data; for order placement a second
    # provider firing after a partial failure could double-place a real
    # order, so exactly one execution provider is ever active).
    execution_provider: str = "mock"
    execution_rate_limit_per_minute: float = 60.0

    # MetaApi.cloud bridge credentials (§0.7 - handled like every other
    # vendor secret: .env-sourced, never logged, never committed - but
    # this one controls a real-money account, treat with extra care).
    metaapi_token: str = ""
    metaapi_account_id: str = ""
    metaapi_request_timeout_seconds: float = 30.0

    # Decided values (spec §4, operator, 2026-08-12/13). `execution_symbol`
    # is the confirmed real Exness symbol (§2/§7) - not `XAUUSD`.
    execution_symbol: str = "XAUUSDc"
    execution_risk_percent: float = 3.0
    execution_max_open_positions: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
