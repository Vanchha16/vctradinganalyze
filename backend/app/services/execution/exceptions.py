class OrderExecutionError(Exception):
    """Base class for execution-provider failures (mirrors
    `app.services.market_data.exceptions.MarketDataProviderError`'s shape,
    §1 of the EA Bot spec)."""


class TransientExecutionError(OrderExecutionError):
    """A retryable failure (timeout, bridge disconnected)."""


class PermanentExecutionError(OrderExecutionError):
    """A non-retryable failure (invalid symbol, order rejected by broker)."""


class ExecutionProviderConfigurationError(OrderExecutionError):
    """The provider is misconfigured (unknown provider name, missing
    required settings/token) - a setup problem, not a runtime failure."""


class AccountDataUnavailableError(TransientExecutionError):
    """Live account balance/equity could not be fetched. Position sizing
    (§5) must reject and log rather than guess when this is raised - never
    fall back to a cached or assumed balance for a real-money account."""


class SymbolSpecificationUnavailableError(TransientExecutionError):
    """The broker's contract/lot-size specification for the configured
    symbol could not be fetched. Same "reject, don't guess" rule as
    `AccountDataUnavailableError` - §5 depends on real lot-step/contract
    data, not general MT5 assumptions."""


class PositionSizingRejectedError(PermanentExecutionError):
    """§5's "reject, don't guess" rule for every unsafe/undefined sizing
    input (zero balance, zero stop distance, computed size below the
    broker's minimum lot). Not a bug or a transient failure - a real,
    expected outcome of a real-money system that must never fabricate a
    position size. Caller (§6) must log this and leave the signal
    `ACTIVE` un-executed rather than retry."""
