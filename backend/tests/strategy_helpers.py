"""Factory functions for building `StrategyEvidenceBundle` fixtures for
Strategy Engine unit tests - reuses `analysis_confidence_helpers`'s
`make_technical_result`/`make_smc_result`/`make_regime_result`."""

from app.services.bbma.types import (
    BBMAConditions,
    BBMADirection,
    BBMAResult,
    BBMASetup,
    BBMASetupKind,
)
from app.services.market_regime.types import MarketRegimeResult
from app.services.risk_management.economic_filter import EconomicFilterResult
from app.services.risk_management.types import LiquidityClassification, MarketSession
from app.services.smc.types import SMCAnalysisResult
from app.services.strategy.types import StrategyEvidenceBundle
from app.services.technical_analysis.types import TechnicalAnalysisResult
from tests.analysis_confidence_helpers import (
    make_regime_result,
    make_smc_result,
    make_technical_result,
)

_NEUTRAL_ECONOMIC = EconomicFilterResult(economic_score=10.0, hard_reject=False, reason=None)


def make_evidence_bundle(
    *,
    technical: TechnicalAnalysisResult | None = None,
    smc: SMCAnalysisResult | None = None,
    market_regime: MarketRegimeResult | None = None,
    overall_confidence: float = 70.0,
    session: MarketSession = MarketSession.LONDON,
    liquidity: LiquidityClassification = LiquidityClassification.NORMAL,
    economic: EconomicFilterResult = _NEUTRAL_ECONOMIC,
    include_evidence: bool = True,
    bbma: BBMAResult | None = None,
) -> StrategyEvidenceBundle:
    if include_evidence:
        technical = technical if technical is not None else make_technical_result()
        smc = smc if smc is not None else make_smc_result()
        market_regime = market_regime if market_regime is not None else make_regime_result()

    return StrategyEvidenceBundle(
        technical=technical,
        # ADR-148: defaults to None, so every pre-existing test keeps
        # asserting exactly what it asserted before - BBMA's checklist
        # simply scores 0/4 with no evidence, which is its own
        # documented behaviour rather than a special case.
        bbma=bbma,
        smc=smc,
        market_regime=market_regime,
        overall_confidence=overall_confidence,
        session=session,
        liquidity=liquidity,
        economic=economic,
    )


def make_bbma_result(
    *,
    kind: BBMASetupKind = BBMASetupKind.EXTREME,
    direction: BBMADirection = BBMADirection.BUY,
    with_setup: bool = True,
) -> BBMAResult:
    """A completed Extreme with its reverse and retest (ADR-158).

    Notes are included because they are what record that a CS Reverse and
    CS Retest were actually found - the difference between a real setup
    and a shape that resembles one.
    """
    setup = (
        BBMASetup(
            kind=kind,
            direction=direction,
            entry_index=146,
            marked_level=4326.95,
            entry_price=4333.75,
            stop_loss=4323.45,
            take_profit=4339.28,
            notes=["Extreme buy at bar 146", "CS Reverse at bar 146", "CS Retest at bar 154"],
        )
        if with_setup
        else None
    )
    return BBMAResult(
        symbol="XAUUSD",
        timeframe="h1",
        setups=[setup] if setup is not None else [],
        conditions=BBMAConditions(
            csm=False,
            csak=False,
            csk=True,
            zzl=True,
            trend_major=direction,
            bb_expanding=True,
        ),
    )
