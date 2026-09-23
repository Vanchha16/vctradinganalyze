"""Strategy and signal settings the super admin can change at runtime (ADR-178).

Database first, `.env` second - ADR-156's rule for API keys, reused. A row
in `system_settings` keyed `runtime.<setting>` wins; with no row, every
caller gets exactly the `.env` value it always did.

**How a stored value reaches the code without touching call sites.** Every
consumer already reads `settings.<name>` at call time, so `refresh()` writes
the stored overrides onto the shared `settings` object. It runs at the start
of every Celery task and on every API request, cached for
`_CACHE_TTL_SECONDS`, so a change is live within that window and needs no
restart.

Three properties keep this safe:

- It only ever writes keys in `REGISTRY`, and only ever restores a key it
  previously overrode. With no rows it changes nothing at all - which also
  keeps it out of the way of tests that set these values directly.
- It snapshots each setting's `.env` value before first overriding it, and
  restores that exact value when the override is removed.
- It is fail-open: if the table cannot be read, the last known values stand.
  A settings lookup must never be why a signal task fails.

Every registered value is immutable (bool, int, str, Decimal, tuple) and
assigned in one statement, which is what makes mutating a shared object
from concurrent requests safe. A mutable value here would break that.
"""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import structlog

from app.config import settings
from app.database.session import SessionLocal
from app.models.system_setting import SystemSetting
from app.services.strategy.types import StrategyName

logger = structlog.get_logger(__name__)

KEY_PREFIX = "runtime."

#: Same window as ADR-156's credential resolver, and stated in the admin UI.
_CACHE_TTL_SECONDS = 30.0
#: The same window, as the API reports it to the admin page.
PROPAGATION_SECONDS = int(_CACHE_TTL_SECONDS)

#: `_MIN_RISK_REWARD_MULTIPLE` in the candidate setup builder. A tight
#: target below twice its stop would produce setups the rest of the
#: pipeline treats as below minimum risk/reward.
MIN_TARGET_TO_STOP = Decimal("2")

Kind = Literal["bool", "int", "decimal", "choice", "strategies"]
Group = Literal["strategies", "tight", "pipeline"]


class RuntimeSettingError(ValueError):
    """A value, or a batch of values, that must not be stored."""


@dataclass(frozen=True)
class RuntimeSetting:
    field: str
    group: Group
    label: str
    help: str
    kind: Kind
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    choices: tuple[str, ...] = ()

    # --- conversions ------------------------------------------------------

    def parse(self, raw: Any) -> Any:
        """A value from the API or the database, as the typed setting value.
        Raises `RuntimeSettingError` with a message fit to show the admin."""
        if self.kind == "bool":
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
                return raw.strip().lower() == "true"
            raise RuntimeSettingError(f"{self.label}: must be on or off.")

        if self.kind in ("int", "decimal"):
            try:
                number = Decimal(str(raw).strip())
            except (InvalidOperation, ValueError):
                raise RuntimeSettingError(f"{self.label}: must be a number.") from None
            if not number.is_finite():
                raise RuntimeSettingError(f"{self.label}: must be a number.")
            if self.kind == "int" and number != number.to_integral_value():
                raise RuntimeSettingError(f"{self.label}: must be a whole number.")
            if self.minimum is not None and number < self.minimum:
                raise RuntimeSettingError(f"{self.label}: must be at least {self.minimum}.")
            if self.maximum is not None and number > self.maximum:
                raise RuntimeSettingError(f"{self.label}: must be at most {self.maximum}.")
            return int(number) if self.kind == "int" else number

        if self.kind == "choice":
            value = str(raw).strip().lower()
            if value not in self.choices:
                raise RuntimeSettingError(
                    f"{self.label}: must be one of {', '.join(self.choices)}."
                )
            return value

        # strategies: a list (API) or a comma-separated string (database)
        items = raw.split(",") if isinstance(raw, str) else list(raw)
        names = {str(i).strip().lower() for i in items if str(i).strip()}
        unknown = sorted(names - set(self.choices))
        if unknown:
            raise RuntimeSettingError(f"Unknown strategy: {', '.join(unknown)}.")
        # Declaration order, so the stored value and the display are stable.
        return tuple(name for name in self.choices if name in names)

    def serialize(self, value: Any) -> str:
        if self.kind == "bool":
            return "true" if value else "false"
        if self.kind == "strategies":
            return ",".join(value)
        return str(value)

    def to_json(self, value: Any) -> Any:
        """The value as the API returns it."""
        if self.kind == "decimal":
            return str(value)
        if self.kind == "strategies":
            return list(value)
        return value


_POINTS = "Price points on XAUUSD."

REGISTRY: tuple[RuntimeSetting, ...] = (
    RuntimeSetting(
        "disabled_strategies",
        "strategies",
        "Disabled strategies",
        "Still scored, never chosen as the primary strategy. With every strategy "
        "disabled, every analysis is WAIT.",
        "strategies",
        choices=tuple(s.value for s in StrategyName),
    ),
    RuntimeSetting(
        "smc_enabled",
        "strategies",
        "SMC-ICT-CRT v1",
        "ADR-183. Its own deterministic path: H4 CRT raid, M5 MSS, FVG/OB entry. "
        "No AI, no generic risk gates, no M1 confirmation. Enable only with BBMA disabled.",
        "bool",
    ),
    RuntimeSetting(
        "tight_m5_enabled",
        "tight",
        "Tight M5 strategy",
        "ADR-176. Checks every 5 minutes, no AI call, publishes immediately.",
        "bool",
    ),
    RuntimeSetting(
        "tight_m5_stop_distance",
        "tight",
        "Tight M5 stop",
        _POINTS,
        "decimal",
        minimum=Decimal("1"),
        maximum=Decimal("50"),
    ),
    RuntimeSetting(
        "tight_m5_target_distance",
        "tight",
        "Tight M5 target",
        _POINTS + " At least 2x the stop.",
        "decimal",
        minimum=Decimal("2"),
        maximum=Decimal("200"),
    ),
    RuntimeSetting(
        "tight_h1_enabled",
        "tight",
        "Tight H1 mode",
        "ADR-176. When on, every H1 signal uses these fixed distances instead of ATR/structure.",
        "bool",
    ),
    RuntimeSetting(
        "tight_h1_stop_distance",
        "tight",
        "Tight H1 stop",
        _POINTS,
        "decimal",
        minimum=Decimal("1"),
        maximum=Decimal("100"),
    ),
    RuntimeSetting(
        "tight_h1_target_distance",
        "tight",
        "Tight H1 target",
        _POINTS + " At least 2x the stop.",
        "decimal",
        minimum=Decimal("2"),
        maximum=Decimal("400"),
    ),
    RuntimeSetting(
        "signal_confirmation_enabled",
        "pipeline",
        "Confirmation",
        "ADR-166. When off, H1 signals publish immediately instead of waiting.",
        "bool",
    ),
    RuntimeSetting(
        "signal_confirmation_timeframe",
        "pipeline",
        "Confirmation timeframe",
        "ADR-177. Which timeframe's break of structure confirms a draft.",
        "choice",
        choices=("m1", "m5", "m15"),
    ),
    RuntimeSetting(
        "signal_confirmation_window_hours",
        "pipeline",
        "Confirmation window (hours)",
        "How long a draft may wait before it is cancelled.",
        "int",
        minimum=Decimal("1"),
        maximum=Decimal("24"),
    ),
    RuntimeSetting(
        "ai_risk_review_mode",
        "pipeline",
        "AI risk review",
        "ADR-167. off = not asked; shadow = recorded only; enforce = a veto turns "
        "the signal into WAIT.",
        "choice",
        choices=("off", "shadow", "enforce"),
    ),
    RuntimeSetting(
        "signal_ttl_hours",
        "pipeline",
        "Pending signal lifetime (hours)",
        "ADR-088. An unfilled signal expires after this.",
        "int",
        minimum=Decimal("1"),
        maximum=Decimal("72"),
    ),
    RuntimeSetting(
        "signal_triggered_ttl_hours",
        "pipeline",
        "Live trade lifetime (hours)",
        "ADR-137. A filled trade that reaches neither target closes after this.",
        "int",
        minimum=Decimal("1"),
        maximum=Decimal("336"),
    ),
)
BY_FIELD: Mapping[str, RuntimeSetting] = {spec.field: spec for spec in REGISTRY}

#: Pairs validated together: a target must stay at least 2x its stop.
_STOP_TARGET_PAIRS = (
    ("tight_m5_stop_distance", "tight_m5_target_distance", "Tight M5"),
    ("tight_h1_stop_distance", "tight_h1_target_distance", "Tight H1"),
)


def storage_key(field_name: str) -> str:
    return f"{KEY_PREFIX}{field_name}"


# --- The overlay -----------------------------------------------------------

#: The `.env` value of each setting, captured before it is first overridden.
_env_defaults: dict[str, Any] = {}
#: Settings currently holding a stored override in this process.
_overridden: set[str] = set()
_last_refresh = float("-inf")


def env_default(field_name: str) -> Any:
    """The `.env` value - what a reset falls back to."""
    if field_name in _env_defaults:
        return _env_defaults[field_name]
    return getattr(settings, field_name)


def apply_rows(rows: Mapping[str, str]) -> None:
    """Bring `settings` in line with `rows` (`{storage_key: raw_value}`).

    Only registered keys, and only restores what this module overrode. A
    stored value that no longer parses - edited by hand, or narrowed by a
    later release - is logged and skipped, leaving the setting at whatever
    it was, rather than taking down the process that tried to read it.
    """
    for spec in REGISTRY:
        key = storage_key(spec.field)
        if key in rows:
            try:
                value = spec.parse(rows[key])
            except RuntimeSettingError as exc:
                logger.warning(
                    "runtime_settings.bad_stored_value", setting=spec.field, error=str(exc)
                )
                continue
            if spec.field not in _env_defaults:
                _env_defaults[spec.field] = getattr(settings, spec.field)
            setattr(settings, spec.field, value)
            _overridden.add(spec.field)
        elif spec.field in _overridden:
            setattr(settings, spec.field, _env_defaults[spec.field])
            _overridden.discard(spec.field)


def refresh(*, force: bool = False, loader: Callable[[], Mapping[str, str]] | None = None) -> None:
    """Reload stored overrides, at most once per `_CACHE_TTL_SECONDS`.

    Called at the start of every Celery task and every API request. The
    timestamp is taken before the query so an unreachable database is
    retried once per window, not hammered by every request.
    """
    global _last_refresh
    now = time.monotonic()
    if not force and now - _last_refresh < _CACHE_TTL_SECONDS:
        return
    _last_refresh = now
    try:
        rows = (loader or _load_rows)()
    except Exception as exc:  # noqa: BLE001 - fail-open is the whole point
        logger.warning("runtime_settings.refresh_failed", error=str(exc))
        return
    apply_rows(rows)


def _load_rows() -> dict[str, str]:
    with SessionLocal() as session:
        stored = (
            session.query(SystemSetting)
            .filter(SystemSetting.key.startswith(KEY_PREFIX, autoescape=True))
            .all()
        )
        return {row.key: row.value for row in stored}


def reset_for_tests() -> None:
    """Undo every override this process applied. Tests only."""
    global _last_refresh
    apply_rows({})
    _env_defaults.clear()
    _last_refresh = float("-inf")


# --- Validating a batch ----------------------------------------------------


def validate_batch(changes: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any | None]:
    """Parse every change and check the result as a whole.

    `changes` maps a setting to its new raw value, or `None` to reset it to
    `.env`. `current` is every setting's effective value right now. Returns
    the parsed changes. Raises on the first problem, having changed
    nothing - so a stop and its target can be changed in one save without
    the first failing against the old value of the second.
    """
    if not changes:
        raise RuntimeSettingError("Nothing to change.")
    unknown = sorted(set(changes) - set(BY_FIELD))
    if unknown:
        raise RuntimeSettingError(f"Unknown setting: {', '.join(unknown)}.")

    parsed: dict[str, Any | None] = {}
    resulting = dict(current)
    for name, raw in changes.items():
        if raw is None:
            parsed[name] = None
            resulting[name] = env_default(name)
        else:
            parsed[name] = BY_FIELD[name].parse(raw)
            resulting[name] = parsed[name]

    for stop_field, target_field, label in _STOP_TARGET_PAIRS:
        stop = Decimal(str(resulting[stop_field]))
        target = Decimal(str(resulting[target_field]))
        if target < stop * MIN_TARGET_TO_STOP:
            raise RuntimeSettingError(
                f"{label}: target {target} must be at least {MIN_TARGET_TO_STOP}x "
                f"the stop ({stop * MIN_TARGET_TO_STOP})."
            )
    return parsed
