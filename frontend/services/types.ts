export type MarketType = "forex" | "metal" | "crypto" | "index";

export type Timeframe = "m1" | "m5" | "m15" | "m30" | "h1" | "h4" | "d1" | "w1" | "mn";

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  market_type: MarketType;
  exchange: string | null;
  base_currency: string | null;
  quote_currency: string | null;
  is_active: boolean;
}

export interface AssetListResponse {
  items: Asset[];
  page: number;
  limit: number;
  total: number;
}

// ---- Technical Analysis ----

export type TrendDirection = "bullish" | "bearish" | "sideways";
export type TrendStrengthLevel = "weak" | "moderate" | "strong" | "very_strong";

export interface ScoreBreakdown {
  trend: number;
  momentum: number;
  oscillator: number;
  volume: number;
  volatility: number;
  support_resistance: number;
  penalties: number;
  total: number;
}

export interface SupportResistanceLevel {
  price: string;
  source: string;
  strength: string;
}

export interface TechnicalAnalysisResponse {
  symbol: string;
  timeframe: Timeframe;
  trend: TrendDirection;
  strength: TrendStrengthLevel;
  technical_score: number;
  score_breakdown: ScoreBreakdown;
  support: SupportResistanceLevel | null;
  resistance: SupportResistanceLevel | null;
  support_levels: SupportResistanceLevel[];
  resistance_levels: SupportResistanceLevel[];
  indicators: Record<string, number>;
  warnings: string[];
  calculated_at: string;
}

// ---- Smart Money Concepts ----

export type MarketStructureState = "bullish" | "bearish" | "range" | "transition";
export type Direction = "bullish" | "bearish";
export type LiquiditySide = "buy_side" | "sell_side";
export type PremiumDiscountPosition = "premium" | "discount" | "equilibrium";
export type SMCEventStatus = string;

export interface SwingClassification {
  kind: string;
  price: string;
  timestamp: string;
  index: number;
}

export interface MarketStructure {
  state: MarketStructureState;
  classifications: SwingClassification[];
}

export interface BOS {
  direction: Direction;
  break_price: string;
  break_time: string;
  strength: number;
  confirmed: boolean;
}

export interface CHOCH {
  previous_trend: MarketStructureState;
  new_trend: MarketStructureState;
  confidence: number;
  confirmation_time: string;
}

export interface OrderBlock {
  direction: Direction;
  zone_high: string;
  zone_low: string;
  created_at: string;
  status: SMCEventStatus;
  touched: boolean;
  mitigated: boolean;
  broken: boolean;
  strength_score: number;
  freshness_score: number;
  volume_confirmed: boolean;
  is_breaker: boolean;
  breaker_confirmed: boolean;
  retest_count: number;
}

export interface FairValueGap {
  direction: Direction;
  gap_high: string;
  gap_low: string;
  created_at: string;
  status: SMCEventStatus;
  gap_size: string;
  priority: string;
}

export interface LiquidityZone {
  side: LiquiditySide;
  level: string;
  touch_count: number;
  status: SMCEventStatus;
  created_at: string;
}

export interface LiquiditySweep {
  side: LiquiditySide;
  level: string;
  sweep_time: string;
  false_breakout: boolean;
}

export interface PremiumDiscount {
  position: PremiumDiscountPosition;
  distance: number;
  range_high: string;
  range_low: string;
  equilibrium: string;
}

export interface Confluence {
  factors: string[];
  confluence_score: number;
}

export interface SMCScoreBreakdown {
  market_structure: number;
  order_blocks: number;
  fair_value_gaps: number;
  liquidity: number;
  premium_discount: number;
  confluence: number;
  penalties: number;
  total: number;
}

export interface SMCAnalysisResponse {
  symbol: string;
  timeframe: Timeframe;
  market_structure: MarketStructure;
  bos: BOS[];
  choch: CHOCH[];
  order_blocks: OrderBlock[];
  fair_value_gaps: FairValueGap[];
  liquidity_zones: LiquidityZone[];
  liquidity_sweeps: LiquiditySweep[];
  premium_discount: PremiumDiscount;
  confluence: Confluence;
  smc_score: number;
  score_breakdown: SMCScoreBreakdown;
  warnings: string[];
  calculated_at: string;
}

// ---- Market Regime ----

export type MarketRegimeState =
  | "trending_bullish"
  | "trending_bearish"
  | "ranging"
  | "accumulation"
  | "distribution"
  | "breakout"
  | "pullback"
  | "reversal"
  | "high_volatility"
  | "low_volatility"
  | "uncertain";

export type VolatilityRegimeState = "very_low" | "low" | "normal" | "high" | "extreme";
export type ExpansionState = "expansion" | "contraction" | "stable";
export type BreakoutDirection = "bullish" | "bearish" | "false_breakout";
export type PullbackDepth = "healthy" | "deep" | "potential_reversal";
export type ReversalDirection = "bullish" | "bearish";

export interface RegimeConfidenceBreakdown {
  trend_clarity: number;
  volatility_clarity: number;
  structural_confirmation: number;
  stability_penalty: number;
  conflict_penalty: number;
  total: number;
}

export interface TrendRegime {
  direction: TrendDirection;
  strength: TrendStrengthLevel;
  structure_state: MarketStructureState;
  aligned: boolean;
}

export interface VolatilityRegime {
  state: VolatilityRegimeState;
  recent_atr_average: number | null;
  baseline_atr_average: number | null;
}

export interface RangeInfo {
  is_ranging: boolean;
  range_width: string | null;
  range_strength: string | null;
}

export interface ExpansionInfo {
  state: ExpansionState;
  ratio: number | null;
}

export interface TransitionInfo {
  shifting: boolean;
  from_hint: MarketRegimeState | null;
  to_hint: MarketRegimeState | null;
  confidence: number;
}

export interface AccumulationDistribution {
  accumulation_score: number;
  distribution_score: number;
}

export interface BreakoutInfo {
  detected: boolean;
  direction: BreakoutDirection | null;
  volume_confirmed: boolean;
}

export interface PullbackReversal {
  pullback_depth: PullbackDepth | null;
  retracement_ratio: number | null;
  reversal_direction: ReversalDirection | null;
  reversal_confidence: number | null;
  exhaustion_warning: string | null;
}

export interface RegimeCandidate {
  regime: MarketRegimeState;
  confidence: number;
  precedence: number;
}

export interface MarketRegimeResponse {
  symbol: string;
  timeframe: Timeframe;
  regime: MarketRegimeState;
  confidence: number;
  confidence_breakdown: RegimeConfidenceBreakdown;
  trend_regime: TrendRegime;
  volatility: VolatilityRegime;
  range: RangeInfo;
  expansion: ExpansionInfo;
  transition: TransitionInfo;
  accumulation_distribution: AccumulationDistribution;
  breakout: BreakoutInfo;
  pullback_reversal: PullbackReversal;
  candidates: RegimeCandidate[];
  warnings: string[];
  calculated_at: string;
}
